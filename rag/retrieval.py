import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

RAG_DIR = Path(__file__).resolve().parent

CHUNKS_FILE = RAG_DIR / "chunks_new.json"
FAISS_FILE = RAG_DIR / "faiss_new.index"

MODEL_NAME = "BAAI/bge-m3"


# ============================================================
# JURISDICTION PROFILES
# ============================================================

JURISDICTION_PROFILES = {
    "India": {
        "India",
        "International",
    },
    "European Union": {
        "European Union",
        "International",
    },
}


# ============================================================
# LOAD KNOWLEDGE BASE
# ============================================================

print("Loading HackGrid knowledge base...")

with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} chunks.")


# ============================================================
# LOAD FAISS
# ============================================================

print("Loading FAISS index...")

index = faiss.read_index(str(FAISS_FILE))

print(f"FAISS vectors: {index.ntotal}")


# ============================================================
# LOAD BGE-M3
# ============================================================

print("Loading BGE-M3...")

embedding_model = SentenceTransformer(
    MODEL_NAME,
    device="cpu",
)

print("BGE-M3 loaded.")


# ============================================================
# VALIDATION
# ============================================================

if len(chunks) != index.ntotal:
    raise RuntimeError(
        f"Knowledge base mismatch: "
        f"{len(chunks)} chunks vs "
        f"{index.ntotal} FAISS vectors."
    )


# ============================================================
# HELPERS
# ============================================================

def _get_jurisdiction(metadata):
    """
    Safely extract jurisdiction from chunk metadata.
    """

    if not isinstance(metadata, dict):
        return None

    value = metadata.get("jurisdiction")

    if value is None:
        return None

    return str(value).strip()


def _validate_jurisdiction(jurisdiction):
    """
    Validate the requested jurisdiction profile.
    """

    if jurisdiction not in JURISDICTION_PROFILES:
        supported = ", ".join(
            JURISDICTION_PROFILES.keys()
        )

        raise ValueError(
                f"Unsupported jurisdiction profile '{jurisdiction}'. "
                f"Supported jurisdiction profiles: {supported}"
        )


# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve(
    query,
    k=8,
    jurisdiction=None,
):
    """
    Retrieve evidence from the HackGrid knowledge base.

    Parameters
    ----------
    query : str
        User query.

    k : int
        Number of final evidence records.

    jurisdiction : str | None
        If None:
            Legacy unrestricted retrieval.

        If "India":
            Only India + International evidence.

        If "European Union":
            Only European Union + International evidence.
    """

    query = str(query).strip()

    if not query:
        return []

    if jurisdiction is not None:
        _validate_jurisdiction(jurisdiction)

    # --------------------------------------------------------
    # QUERY EMBEDDING
    # --------------------------------------------------------

    query_embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True,
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32",
    )

    # --------------------------------------------------------
    # DETERMINE SEARCH SIZE
    # --------------------------------------------------------

    if jurisdiction is None:
        candidate_k = min(
            len(chunks),
            max(k, 1),
        )
    else:
        # Search broadly first because jurisdiction filtering
        # happens after FAISS retrieval.
        candidate_k = min(
            len(chunks),
            max(k * 10, 100),
        )

    distances, indices = index.search(
        query_embedding,
        candidate_k,
    )

    # --------------------------------------------------------
    # JURISDICTION FILTER
    # --------------------------------------------------------

    allowed_jurisdictions = None

    if jurisdiction is not None:
        allowed_jurisdictions = (
            JURISDICTION_PROFILES[jurisdiction]
        )

    # --------------------------------------------------------
    # BUILD RESULTS
    # --------------------------------------------------------

    results = []

    for original_rank, (distance, idx) in enumerate(
        zip(
            distances[0],
            indices[0],
        ),
        start=1,
    ):

        if idx == -1:
            continue

        chunk = chunks[idx]

        metadata = chunk.get(
            "metadata",
            {},
        )

        chunk_jurisdiction = _get_jurisdiction(
            metadata
        )

        # ----------------------------------------------------
        # JURISDICTION FILTER
        # ----------------------------------------------------

        if allowed_jurisdictions is not None:

            if (
                chunk_jurisdiction
                not in allowed_jurisdictions
            ):
                continue

        # ----------------------------------------------------
        # APPEND RESULT
        # ----------------------------------------------------

        results.append(
            {
                "rank": len(results) + 1,
                "original_rank": original_rank,
                "distance": float(distance),
                "text": chunk["text"],
                "metadata": metadata,
            }
        )

        if len(results) >= k:
            break

    return results


# ============================================================
# SIMPLE TEST
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 80)
    print("HACKGRID JURISDICTION-AWARE RETRIEVAL TEST")
    print("=" * 80)

    query = (
        "5G network slicing security requirements"
    )

    for jurisdiction in [
        "India",
        "European Union",
    ]:

        print(
            f"\n--- {jurisdiction} ---"
        )

        results = retrieve(
            query,
            k=8,
            jurisdiction=jurisdiction,
        )

        print(
            f"Returned {len(results)} evidence records."
        )

        jurisdictions = sorted(
            {
                _get_jurisdiction(
                    item.get("metadata", {})
                )
                for item in results
            }
        )

        print(
            "Jurisdictions:",
            jurisdictions,
        )

        for item in results[:3]:

            metadata = item.get(
                "metadata",
                {},
            )

            print(
                f"{item['rank']}. "
                f"{metadata.get('document', 'Unknown')} | "
                f"{metadata.get('jurisdiction', 'Unknown')}"
            )