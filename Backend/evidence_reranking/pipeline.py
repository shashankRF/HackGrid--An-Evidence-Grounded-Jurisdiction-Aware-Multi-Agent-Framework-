from typing import Any, Dict, List

from .reranker import EvidenceReranker
from .evidence_analyzer import analyze_evidence
from .counter_evidence import build_counter_query


class EvidenceRankingPipeline:

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
    ):
        self.reranker = EvidenceReranker(
            model_name=model_name
        )

    def run(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        final_top_k: int = 8,
    ) -> Dict[str, Any]:

        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=final_top_k,
        )

        analysis = analyze_evidence(
            candidates=reranked,
            query=query,
            final_top_k=final_top_k,
        )

        return {
            "query": query,
            "reranked_evidence": reranked,
            "evidence_analysis": analysis.to_dict(),
            "counter_evidence_query": build_counter_query(
                query
            ),
        }