from __future__ import annotations

from typing import Any, Dict, List

from .models import EvidenceMetadata


def build_evidence_metadata(
    result: Dict[str, Any],
    rank: int | None = None,
) -> EvidenceMetadata:
    """
    Convert an existing RAG retrieval result into the
    normalized EvidenceMetadata structure.

    Original provenance is preserved.
    """

    metadata = result.get("metadata", {}) or {}

    retrieval_rank = (
        rank
        if rank is not None
        else result.get("rank")
    )

    return EvidenceMetadata(
        document=metadata.get("document"),
        publisher=metadata.get("publisher"),
        source_type=(
            metadata.get("source_type")
            or metadata.get("document_type")
        ),
        jurisdiction=metadata.get("jurisdiction"),
        page=metadata.get("page"),
        section=metadata.get("section"),
        clause=metadata.get("clause"),
        chunk_id=metadata.get(
            "chunk_id",
            result.get("chunk_id"),
        ),
        retrieval_rank=retrieval_rank,
        version=metadata.get("version"),
        publication_date=metadata.get(
            "publication_date"
        ),
        effective_date=metadata.get(
            "effective_date"
        ),
        expiry_date=metadata.get(
            "expiry_date"
        ),
    )


def build_evidence_record(
    result: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    """
    Convert one real RAG retrieval result into an
    audit-ready evidence record.

    EV-XXX is an internal HackGrid evidence identifier.
    The original chunk_id and text_hash remain the
    authoritative provenance identifiers.
    """

    metadata = result.get("metadata", {}) or {}

    evidence_id = f"EV-{index:03d}"

    return {
        "evidence_id": evidence_id,

        "retrieval": {
            "rank": result.get("rank", index),
            "distance": result.get("distance"),
        },

        "provenance": {
            "document": metadata.get("document"),
            "source_file": metadata.get("source_file"),
            "folder": metadata.get("folder"),
            "jurisdiction": metadata.get("jurisdiction"),
            "document_type": metadata.get("document_type"),
            "page": metadata.get("page"),
            "section": metadata.get("section"),
            "clause": metadata.get("clause"),
            "chunk_id": metadata.get(
                "chunk_id",
                result.get("chunk_id"),
            ),
            "language": metadata.get("language"),
            "text_hash": metadata.get("text_hash"),
        },

        "text": result.get("text", ""),

        "normalized_metadata": {
            "document": metadata.get("document"),
            "publisher": metadata.get("publisher"),
            "source_type": (
                metadata.get("source_type")
                or metadata.get("document_type")
            ),
            "jurisdiction": metadata.get("jurisdiction"),
            "page": metadata.get("page"),
            "section": metadata.get("section"),
            "clause": metadata.get("clause"),
            "chunk_id": metadata.get(
                "chunk_id",
                result.get("chunk_id"),
            ),
            "retrieval_rank": result.get(
                "rank",
                index,
            ),
            "version": metadata.get("version"),
            "publication_date": metadata.get(
                "publication_date"
            ),
            "effective_date": metadata.get(
                "effective_date"
            ),
            "expiry_date": metadata.get(
                "expiry_date"
            ),
        },
    }


def adapt_retrieval_results(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert the complete RAG retrieval result set
    into Evidence Engine records.
    """

    evidence_records = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        evidence_records.append(
            build_evidence_record(
                result=result,
                index=index,
            )
        )

    return evidence_records