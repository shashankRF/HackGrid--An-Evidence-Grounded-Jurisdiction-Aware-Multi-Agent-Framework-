"""
HackGrid Multi-KB Retrieval Engine

Searches:
    1. MAIN KB
    2. MARITIME KB
    3. DEFENCE KB

The Main KB is ALWAYS searched.

Domain KBs are additional evidence sources.
They never replace the Main KB.

This module does NOT modify or rebuild any existing index.
"""

from pathlib import Path
import json
import numpy as np
import faiss

from sentence_transformers import SentenceTransformer


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MAIN_DIR = BASE_DIR

MARITIME_DIR = BASE_DIR / "MARITIME CHUNKS"

DEFENCE_DIR = BASE_DIR / "DEFENCE CHUNKS"


# ============================================================
# INDEX FILES
# ============================================================

INDEX_CONFIG = {

    "MAIN": {
        "index": MAIN_DIR / "faiss_new.index",
        "chunks": MAIN_DIR / "chunks_new.json",
        "embeddings": MAIN_DIR / "embeddings_new.npy",
    },

    "MARITIME": {
        "index": MARITIME_DIR / "maritime_faiss.index",
        "chunks": MARITIME_DIR / "maritime_chunks.json",
        "embeddings": MARITIME_DIR / "maritime_embeddings.npy",
    },

    "DEFENCE": {
        "index": DEFENCE_DIR / "defence_faiss.index",
        "chunks": DEFENCE_DIR / "defence_chunks.json",
        "embeddings": DEFENCE_DIR / "defence_embeddings.npy",
    }
}


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "BAAI/bge-m3"


# ============================================================
# RETRIEVAL PARAMETERS
# ============================================================

DEFAULT_CANDIDATES_PER_KB = 15

DEFAULT_FINAL_K = 10


# ============================================================
# MULTI-KB RETRIEVER
# ============================================================

class MultiKBRetriever:

    def __init__(self):

        print()
        print("=" * 70)
        print("HACKGRID MULTI-KB RETRIEVER")
        print("=" * 70)

        self.model = SentenceTransformer(
            MODEL_NAME,
            device="cpu"
        )

        self.indexes = {}

        self.chunks = {}

        self.embeddings = {}

        self._load_all_kbs()


    # ========================================================
    # LOAD KBs
    # ========================================================

    def _load_all_kbs(self):

        for kb_name, config in INDEX_CONFIG.items():

            print()
            print(f"Loading {kb_name} KB...")

            index_path = config["index"]

            chunks_path = config["chunks"]

            embeddings_path = config["embeddings"]


            # ------------------------------------------------
            # Check files
            # ------------------------------------------------

            for path in [
                index_path,
                chunks_path,
                embeddings_path
            ]:

                if not path.exists():

                    raise FileNotFoundError(
                        f"{kb_name} KB missing file:\n{path}"
                    )


            # ------------------------------------------------
            # Load FAISS
            # ------------------------------------------------

            index = faiss.read_index(
                str(index_path)
            )


            # ------------------------------------------------
            # Load chunks
            # ------------------------------------------------

            with open(
                chunks_path,
                "r",
                encoding="utf-8"
            ) as f:

                chunks = json.load(f)


            # ------------------------------------------------
            # Load embeddings
            # ------------------------------------------------

            embeddings = np.load(
                embeddings_path,
                mmap_mode="r"
            )


            # ------------------------------------------------
            # Validate
            # ------------------------------------------------

            if index.ntotal != len(chunks):

                raise ValueError(
                    f"{kb_name}: FAISS vectors "
                    f"({index.ntotal}) != chunks "
                    f"({len(chunks)})"
                )


            if len(embeddings) != len(chunks):

                raise ValueError(
                    f"{kb_name}: embeddings "
                    f"({len(embeddings)}) != chunks "
                    f"({len(chunks)})"
                )


            if index.d != embeddings.shape[1]:

                raise ValueError(
                    f"{kb_name}: FAISS dimension "
                    f"({index.d}) != embedding dimension "
                    f"({embeddings.shape[1]})"
                )


            self.indexes[kb_name] = index

            self.chunks[kb_name] = chunks

            self.embeddings[kb_name] = embeddings


            print(
                f"  Vectors:    {index.ntotal}"
            )

            print(
                f"  Dimension:  {index.d}"
            )

            print(
                f"  Chunks:     {len(chunks)}"
            )


        print()
        print("=" * 70)
        print("ALL KNOWLEDGE BASES LOADED")
        print("=" * 70)


    # ========================================================
    # EMBED QUERY
    # ========================================================

    def _embed_query(self, query):

        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embedding.astype(
            "float32"
        )


    # ========================================================
    # SEARCH ONE KB
    # ========================================================

    def _search_kb(
        self,
        query_vector,
        kb_name,
        top_k
    ):

        index = self.indexes[kb_name]

        chunks = self.chunks[kb_name]


        distances, ids = index.search(
            query_vector,
            top_k
        )


        results = []


        for rank, (
            score,
            vector_id
        ) in enumerate(
            zip(
                distances[0],
                ids[0]
            ),
            start=1
        ):

            if vector_id < 0:
                continue


            chunk = chunks[vector_id]


            result = {

                "kb": kb_name,

                "rank_in_kb": rank,

                "score": float(score),

                "vector_id": int(vector_id),

                "chunk": chunk
            }


            results.append(
                result
            )


        return results


    # ========================================================
    # SEARCH MULTIPLE KBs
    # ========================================================

    def search(
        self,
        query,
        domains=None,
        candidates_per_kb=DEFAULT_CANDIDATES_PER_KB,
        final_k=DEFAULT_FINAL_K
    ):

        if not query or not query.strip():

            raise ValueError(
                "Query cannot be empty."
            )


        # ----------------------------------------------------
        # MAIN is ALWAYS searched
        # ----------------------------------------------------

        selected_kbs = [
            "MAIN"
        ]


        # ----------------------------------------------------
        # Add requested domain KBs
        # ----------------------------------------------------

        if domains:

            if isinstance(
                domains,
                str
            ):

                domains = [
                    domains
                ]


            for domain in domains:

                domain = domain.upper().strip()


                if domain in [
                    "MARITIME",
                    "DEFENCE"
                ]:

                    if domain not in selected_kbs:

                        selected_kbs.append(
                            domain
                        )


        # ----------------------------------------------------
        # Embed query
        # ----------------------------------------------------

        query_vector = self._embed_query(
            query
        )


        # ----------------------------------------------------
        # Search each selected KB
        # ----------------------------------------------------

        all_results = []


        for kb_name in selected_kbs:

            results = self._search_kb(
                query_vector,
                kb_name,
                candidates_per_kb
            )


            all_results.extend(
                results
            )


        # ----------------------------------------------------
        # Sort globally by semantic score
        # ----------------------------------------------------

        all_results.sort(
            key=lambda x: x["score"],
            reverse=True
        )


        # ----------------------------------------------------
        # Deduplicate
        # ----------------------------------------------------

        deduplicated = []

        seen = set()


        for result in all_results:

            chunk = result["chunk"]


            # Try stable ID first
            chunk_id = chunk.get(
                "chunk_id"
            )


            source = chunk.get(
                "source_file",
                chunk.get(
                    "document",
                    ""
                )
            )


            page = chunk.get(
                "page",
                chunk.get(
                    "page_number",
                    ""
                )
            )


            text = chunk.get(
                "text",
                chunk.get(
                    "content",
                    ""
                )
            )


            dedupe_key = (
                result["kb"],
                chunk_id,
                source,
                page,
                text[:200]
            )


            if dedupe_key in seen:

                continue


            seen.add(
                dedupe_key
            )


            deduplicated.append(
                result
            )


        # ----------------------------------------------------
        # Final results
        # ----------------------------------------------------

        final_results = deduplicated[
            :final_k
        ]


        # ----------------------------------------------------
        # Add global rank
        # ----------------------------------------------------

        for rank, result in enumerate(
            final_results,
            start=1
        ):

            result["global_rank"] = rank


        return {

            "query": query,

            "searched_kbs": selected_kbs,

            "candidate_count": len(
                all_results
            ),

            "final_count": len(
                final_results
            ),

            "results": final_results
        }


# ============================================================
# SIMPLE TEST MODE
# ============================================================

if __name__ == "__main__":

    import argparse


    parser = argparse.ArgumentParser(
        description="HackGrid Multi-KB Retriever"
    )


    parser.add_argument(
        "--query",
        required=True
    )


    parser.add_argument(
        "--domains",
        nargs="*",
        default=[]
    )


    parser.add_argument(
        "--candidates",
        type=int,
        default=15
    )


    parser.add_argument(
        "--top-k",
        type=int,
        default=10
    )


    args = parser.parse_args()


    retriever = MultiKBRetriever()


    output = retriever.search(

        query=args.query,

        domains=args.domains,

        candidates_per_kb=args.candidates,

        final_k=args.top_k
    )


    print()
    print("=" * 70)
    print("SEARCH RESULT")
    print("=" * 70)

    print(
        f"Query: {output['query']}"
    )

    print(
        f"KBs searched: "
        f"{', '.join(output['searched_kbs'])}"
    )

    print(
        f"Candidates: "
        f"{output['candidate_count']}"
    )

    print(
        f"Final evidence: "
        f"{output['final_count']}"
    )


    for result in output["results"]:

        chunk = result["chunk"]

        print()
        print("-" * 70)

        print(
            f"Global Rank: "
            f"{result['global_rank']}"
        )

        print(
            f"KB: "
            f"{result['kb']}"
        )

        print(
            f"Score: "
            f"{result['score']:.4f}"
        )

        print(
            f"Source: "
            f"{chunk.get('source_file', 'N/A')}"
        )

        print(
            f"Page: "
            f"{chunk.get('page', 'N/A')}"
        )

        print(
            f"Chunk ID: "
            f"{chunk.get('chunk_id', 'N/A')}"
        )

        print()

        print(
            chunk.get(
                "text",
                chunk.get(
                    "content",
                    ""
                )
            )[:1000]
        )