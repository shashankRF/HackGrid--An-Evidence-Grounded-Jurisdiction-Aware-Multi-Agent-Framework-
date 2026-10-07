import json
import time

from Backend.query_analysis.domain_classifier import classify

from rag.retrieval import retrieve

from Backend.evidence_reranking.pipeline import (
    EvidenceRankingPipeline,
)

from Backend.evidence_reranking.evidence_analyzer import (
    analyze_evidence,
)

from Backend.governance import evaluate_governance

from Backend.evidence_engine.rag_adapter import (
    adapt_retrieval_results,
)

from Backend.evidence_engine.llm_classifier import (
    classify_evidence,
)

from Backend.evidence_engine.validator import (
    validate_evidence_consistency,
)

from Backend.evidence_engine.claim_builder import (
    build_claim_assessment,
)

from Backend.evidence_engine.engine import (
    EvidenceEngine,
)

from Backend.evidence_engine.absence_protocol import (
    build_absence_verification,
    absence_verification_to_dict,
)

from Backend.evidence_engine.gap_adapter import (
    build_gap_input,
)

from Backend.final_synthesis import (
    synthesize_final_assessment,
)

from Backend.risk_integration_v2 import (
    assess_with_evidence_engine,
    risk_assessment_to_dict,
)

from Backend.risk_engine.models import (
    DecisionContext,
    DecisionImpact,
    AuthorityRequirement,
    AIAnalysis,
)

from Backend.audit.recorder import (
    create_audit_record,
    append_audit_record,
)


# ============================================================
# DEFAULT QUESTION
# ============================================================

QUESTION = (
    "What security requirements apply to 5G network slicing in India?"
)


# ============================================================
# SUPPORTED JURISDICTIONS
# ============================================================

SUPPORTED_JURISDICTIONS = {
    "India",
    "European Union",
}


# ============================================================
# EXECUTION CONFIGURATION
# ============================================================

FULL_CONFIG = {
    "retrieval_k": 20,
    "rerank_candidate_limit": None,
    "rerank_top_k": 8,
    "counter_retrieval_k": 20,
    "counter_rerank_candidate_limit": None,
    "counter_rerank_top_k": 8,
    "final_evidence_k": 8,
}


DEMO_CONFIG = {
    # Compact execution for live frontend scenarios.
    #
    # The goal is to preserve the complete pipeline while
    # drastically reducing expensive local cross-encoder work.
    "retrieval_k": 10,
    "rerank_candidate_limit": 5,
    "rerank_top_k": 3,
    "counter_retrieval_k": 6,
    "counter_rerank_candidate_limit": 4,
    "counter_rerank_top_k": 2,
    "final_evidence_k": 4,
}


def _get_execution_config(demo_mode=False):
    """
    Return a copy of the execution configuration.

    DEMO mode is intended for interactive scenario execution.
    FULL mode is intended for complete backend analysis.
    """

    return dict(
        DEMO_CONFIG if demo_mode else FULL_CONFIG
    )


# ============================================================
# EVIDENCE ASSESSMENT SERIALIZATION
# ============================================================

def _assessment_to_dict(assessment):

    return {
        "overall_status": (
            assessment.overall_status.value
        ),
        "overall_strength": (
            assessment.overall_strength.value
        ),
        "supporting_count": (
            assessment.supporting_count
        ),
        "contradicting_count": (
            assessment.contradicting_count
        ),
        "primary_source_count": (
            assessment.primary_source_count
        ),
        "official_source_count": (
            assessment.official_source_count
        ),
        "source_diversity": (
            assessment.source_diversity
        ),
        "overall_confidence": (
            assessment.overall_confidence
        ),
        "missing_evidence": list(
            assessment.missing_evidence
        ),
    }


# ============================================================
# EVIDENCE DEDUPLICATION
# ============================================================

def _evidence_key(item):

    metadata = item.get(
        "metadata",
        {},
    )

    return (
        metadata.get("chunk_id")
        or metadata.get("id")
        or metadata.get("document")
        or metadata.get("source_file")
        or item.get("evidence_id")
        or item.get("original_rank")
    )


def _merge_evidence(
    primary,
    counter,
):

    combined = []
    seen = set()

    for item in primary + counter:

        key = _evidence_key(item)

        if key in seen:
            continue

        seen.add(key)
        combined.append(item)

    return combined


# ============================================================
# CACHED EVIDENCE RANKING PIPELINE
# ============================================================

_cached_ranking_pipeline = None


def get_ranking_pipeline() -> EvidenceRankingPipeline:
    global _cached_ranking_pipeline

    if _cached_ranking_pipeline is None:
        _cached_ranking_pipeline = EvidenceRankingPipeline()

    return _cached_ranking_pipeline


# ============================================================
# FULL HACKGRID PIPELINE
# ============================================================

def run_pipeline(
    question,
    jurisdiction="India",
    demo_mode=False,
    notes=None,
):

    t_start = time.perf_counter()

    performance = {}

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    # ========================================================
    # EXECUTION CONFIGURATION
    # ========================================================

    execution_config = _get_execution_config(
        demo_mode
    )

    primary_k = execution_config[
        "retrieval_k"
    ]

    primary_rerank_candidate_limit = execution_config[
        "rerank_candidate_limit"
    ]

    primary_rerank_top_k = execution_config[
        "rerank_top_k"
    ]

    counter_k = execution_config[
        "counter_retrieval_k"
    ]

    counter_rerank_candidate_limit = execution_config[
        "counter_rerank_candidate_limit"
    ]

    counter_rerank_top_k = execution_config[
        "counter_rerank_top_k"
    ]

    final_evidence_limit = execution_config[
        "final_evidence_k"
    ]

    # ========================================================
    # JURISDICTION VALIDATION
    # ========================================================

    if jurisdiction not in SUPPORTED_JURISDICTIONS:

        supported = ", ".join(
            sorted(SUPPORTED_JURISDICTIONS)
        )

        raise ValueError(
            f"Unsupported jurisdiction '{jurisdiction}'. "
            f"Supported jurisdictions: {supported}"
        )

    # ========================================================
    # 0. DOMAIN + INTENT CLASSIFICATION
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[0/9] Domain + Intent classification..."
    )

    classification = classify(
        question
    )

    performance[
        "classification_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    print(
        "Domain:",
        classification.get("domain"),
    )

    print(
        "Intent:",
        classification.get("intent"),
    )

    print(
        "Confidence:",
        classification.get("confidence"),
    )

    print(
        "Jurisdiction:",
        jurisdiction,
    )

    print(
        "Execution Mode:",
        "DEMO" if demo_mode else "FULL",
    )

    print("=" * 80)

    print(
        "HACKGRID -- "
        + (
            "COMPACT DEMO"
            if demo_mode
            else "FULL"
        )
        + " EVIDENCE-AWARE PIPELINE"
    )

    print("=" * 80)

    primary_domain = (
        classification.get("domain")
        or classification.get(
            "primary_domain"
        )
    )

    secondary = classification.get(
        "secondary_domains",
        [],
    )

    detected_domains = (
        [primary_domain]
        if primary_domain
        else []
    ) + (
        secondary
        if isinstance(
            secondary,
            list,
        )
        else []
    )

    # ========================================================
    # 1. JURISDICTION-AWARE MULTI-KB RETRIEVAL
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[1/9] Jurisdiction-aware multi-KB retrieval..."
    )

    results = retrieve(
        question,
        k=primary_k,
        jurisdiction=jurisdiction,
        domains=detected_domains,
    )

    performance[
        "retrieval_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    if not results:
        raise RuntimeError(
            "RAG returned no evidence for the "
            f"{jurisdiction} jurisdiction."
        )

    kb_distribution = {}

    for r in results:

        k_name = (
            r.get("kb")
            or r.get(
                "metadata",
                {},
            ).get(
                "kb",
                "MAIN",
            )
        )

        kb_distribution[k_name] = (
            kb_distribution.get(
                k_name,
                0,
            )
            + 1
        )

    print(
        f"Retrieved {len(results)} candidate "
        f"evidence records for {jurisdiction}. "
        f"KBs: {kb_distribution}"
    )

    # ========================================================
    # 1B. PRIMARY EVIDENCE RERANKING
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[1B/9] Top-K reranking + evidence analysis..."
    )

    evidence_ranking_pipeline = (
        get_ranking_pipeline()
    )

    ranking_result = (
        evidence_ranking_pipeline.run(
            query=question,

            candidates=results,

            final_top_k=(
                primary_rerank_top_k
            ),

            candidate_limit=(
                primary_rerank_candidate_limit
            ),
        )
    )

    reranked_results = (
        ranking_result[
            "reranked_evidence"
        ]
    )

    if not reranked_results:
        raise RuntimeError(
            "Reranking returned no evidence."
        )

    performance[
        "reranking_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    print(
        f"Reranked to {len(reranked_results)} "
        "primary evidence records."
    )

    counter_evidence_query = (
        ranking_result[
            "counter_evidence_query"
        ]
    )

    # ========================================================
    # 1C. JURISDICTION-AWARE COUNTER EVIDENCE
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[1C/9] Counter-evidence retrieval..."
    )

    counter_results = retrieve(
        counter_evidence_query,
        k=counter_k,
        jurisdiction=jurisdiction,
        domains=detected_domains,
    )

    print(
        f"Retrieved {len(counter_results)} "
        "counter-evidence candidates."
    )

    counter_ranking_result = (
        evidence_ranking_pipeline.run(
            query=counter_evidence_query,

            candidates=counter_results,

            final_top_k=(
                counter_rerank_top_k
            ),

            candidate_limit=(
                counter_rerank_candidate_limit
            ),
        )
    )

    counter_reranked_results = (
        counter_ranking_result[
            "reranked_evidence"
        ]
    )

    performance[
        "counter_evidence_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    print(
        f"Reranked to {len(counter_reranked_results)} "
        "counter-evidence records."
    )

    # ========================================================
    # 1D. MERGE + DEDUPLICATE
    # ========================================================

    print(
        "\n[1D/9] Merging evidence..."
    )

    combined_candidates = _merge_evidence(
        reranked_results,
        counter_reranked_results,
    )

    print(
        f"Combined unique evidence: "
        f"{len(combined_candidates)}"
    )

    if not combined_candidates:
        raise RuntimeError(
            "No combined evidence available."
        )

    # ========================================================
    # 1E. SUPPORTING / CONTRADICTING / CONTEXTUAL
    # ========================================================

    print(
        "\n[1E/9] Evidence role analysis..."
    )

    combined_analysis = analyze_evidence(
        candidates=combined_candidates,
        query=question,
        final_top_k=final_evidence_limit,
    )

    ranking_evidence_analysis = (
        combined_analysis.to_dict()
    )

    print(
        "Supporting:",
        len(
            ranking_evidence_analysis[
                "supporting_evidence"
            ]
        ),
    )

    print(
        "Contradicting:",
        len(
            ranking_evidence_analysis[
                "contradicting_evidence"
            ]
        ),
    )

    print(
        "Contextual:",
        len(
            ranking_evidence_analysis[
                "contextual_evidence"
            ]
        ),
    )

    print(
        "Evidence gaps:",
        len(
            ranking_evidence_analysis[
                "evidence_gaps"
            ]
        ),
    )

    # ========================================================
    # 1F. FINAL TOP-K
    # ========================================================

    combined_candidates.sort(
        key=lambda item: item.get(
            "reranker_score",
            0.0,
        ),
        reverse=True,
    )

    final_evidence = (
        combined_candidates[
            :final_evidence_limit
        ]
    )

    if not final_evidence:
        raise RuntimeError(
            "Final evidence selection returned no evidence."
        )

    if demo_mode:

        for ev in final_evidence:

            ev_text = str(
                ev.get(
                    "text",
                    "",
                )
            ).strip()

            if len(ev_text) > 1000:

                ev["text"] = (
                    ev_text[:1000]
                    + "\n"
                    "[Truncated for compact demo analysis]"
                )

    print(
        f"Final evidence selected: "
        f"{len(final_evidence)}"
    )

    # Preserve existing RAG adapter contract.

    evidence_records = (
        adapt_retrieval_results(
            final_evidence
        )
    )

    print(
        f"Adapted evidence records: "
        f"{len(evidence_records)}"
    )

    # ========================================================
    # 2. GPT-OSS EVIDENCE CLASSIFICATION
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[2/9] GPT-OSS evidence classification..."
    )

    evidence_classification = (
        classify_evidence(
            claim=question,
            evidence_records=evidence_records,
            demo_mode=demo_mode,
        )
    )

    if (
        evidence_classification.get(
            "status"
        )
        != "SUCCESS"
    ):

        err_msg = (
            evidence_classification.get(
                "error"
            )
            or evidence_classification.get(
                "status"
            )
        )

        print(
            f"Evidence classification failed: "
            f"{err_msg}"
        )

        raise RuntimeError(
            f"Evidence classification failed: "
            f"{err_msg}"
        )

    validation = (
        validate_evidence_consistency(
            classifications=(
                evidence_classification
            ),
            evidence_records=(
                evidence_records
            ),
        )
    )

    if not validation["valid"]:

        raise RuntimeError(
            "Evidence consistency validation failed: "
            + str(
                validation["errors"]
            )
        )

    performance[
        "evidence_classification_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    print(
        "Evidence classification: PASS"
    )

    # ========================================================
    # 3. EVIDENCE ENGINE
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[3/9] Evidence Engine..."
    )

    claim = build_claim_assessment(
        evidence_classification,
        evidence_records,
    )

    evidence_engine = EvidenceEngine()

    evidence_assessment = (
        evidence_engine.assess(
            claims=[
                claim
            ]
        )
    )

    evidence_dict = (
        _assessment_to_dict(
            evidence_assessment
        )
    )

    performance[
        "evidence_engine_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    print(
        "Evidence status:",
        evidence_dict[
            "overall_status"
        ],
    )

    # ========================================================
    # 4. ABSENCE VERIFICATION
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[4/9] Absence Verification..."
    )

    absence = build_absence_verification(
        claim=question,

        evidence_records=evidence_records,

        search_scope=(
            "HackGrid RAG knowledge base; "
            f"jurisdiction={jurisdiction}; "
            f"{len(results)}-candidate "
            "jurisdiction-filtered retrieval "
            "with reranking and counter-evidence search"
        ),

        authoritative_jurisdictions=[
            jurisdiction
        ],
    )

    absence_dict = (
        absence_verification_to_dict(
            absence
        )
    )

    performance[
        "absence_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    # ========================================================
    # 5. GAP ANALYSIS
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[5/9] Gap Analysis..."
    )

    gap_input = build_gap_input(
        evidence_assessment=(
            evidence_assessment
        ),

        absence_verifications=[
            absence_dict
        ],

        question=question,
    )

    performance[
        "gap_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    # ========================================================
    # 6. EXISTING RISK + AUTHORITY ENGINE
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[6/9] Risk Engine..."
    )

    risk_context = DecisionContext(
        domain=(
            classification.get(
                "domain",
                "General Evidence",
            )
        ),

        decision_impact=(
            DecisionImpact.REGULATORY
        ),

        consequence_score=85,

        authority_requirement=(
            AuthorityRequirement.SENIOR_AUTHORITY
        ),

        sensitive_information=True,

        external_action=True,

        production_change=False,

        legal_or_regulatory_interpretation=True,

        affects_public_safety=True,

        affects_critical_infrastructure=True,
    )

    ai_analysis = AIAnalysis(
        confidence=max(
            0.0,
            min(
                1.0,
                evidence_assessment.overall_confidence,
            ),
        ),

        factual_claims=len(
            evidence_classification.get(
                "classifications",
                [],
            )
        ),

        supported_claims=(
            evidence_assessment.supporting_count
        ),

        unsupported_claims=len(
            evidence_assessment.missing_evidence
        ),

        hallucination_risk=max(
            0.0,
            min(
                1.0,
                1.0
                - evidence_assessment.overall_confidence,
            ),
        ),

        novel_situation=False,
    )

    risk_assessment = (
        assess_with_evidence_engine(
            decision_context=risk_context,
            evidence_assessment=(
                evidence_assessment
            ),
            ai_analysis=ai_analysis,
        )
    )

    risk_dict = (
        risk_assessment_to_dict(
            risk_assessment
        )
    )

    performance[
        "risk_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    print(
        "Risk:",
        risk_dict["risk_level"],
        risk_dict["risk_score"],
        risk_dict["escalation_level"],
    )

    # ========================================================
    # 7. FINAL GPT-OSS SYNTHESIS
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[7/9] Final GPT-OSS synthesis..."
    )

    final = (
        synthesize_final_assessment(
            question=question,
            evidence_records=evidence_records,
            classification=evidence_classification,
            evidence_assessment=evidence_dict,
            absence_verifications=[
                absence_dict
            ],
            gap_input=gap_input,
            risk_assessment=risk_dict,
            demo_mode=demo_mode,
            counter_evidence_analysis=ranking_evidence_analysis,
        )
    )

    performance[
        "synthesis_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    # ========================================================
    # GOVERNANCE
    # ========================================================

    governance = evaluate_governance(
        question=question,
        evidence_assessment=evidence_dict,
        gap_analysis=gap_input,
        risk_assessment=risk_dict,
        final_synthesis=final,
        classification=evidence_classification,
    )

    # ========================================================
    # 8. CLAIM -> EVIDENCE MAPPINGS
    # ========================================================

    print(
        "\n[8/9] Building claim -> evidence mappings..."
    )

    mappings = []

    for claim_item in final.get(
        "claims",
        [],
    ):

        mappings.append(
            {
                "claim_id": claim_item.get(
                    "claim_id"
                ),

                "claim": claim_item.get(
                    "claim"
                ),

                "status": claim_item.get(
                    "status"
                ),

                "evidence_ids": claim_item.get(
                    "evidence_ids",
                    [],
                ),

                "confidence": claim_item.get(
                    "confidence",
                    0.0,
                ),
            }
        )

    # ========================================================
    # 9. AUDIT
    # ========================================================

    t_stage = time.perf_counter()

    print(
        "\n[9/9] Writing audit trail..."
    )

    audit_record = create_audit_record(
        question=question,

        model="openai/gpt-oss-120b",

        retrieved_evidence=evidence_records,

        evidence_classification=(
            evidence_classification
        ),

        evidence_assessment=evidence_dict,

        absence_verification=[
            absence_dict
        ],

        gap_analysis=gap_input,

        risk_assessment=risk_dict,

        final_synthesis=final,

        claim_evidence_mappings=mappings,

        human_review_required=(
            risk_dict[
                "human_review_required"
            ]
        ),

        final_decision=(
            "PENDING_HUMAN_REVIEW"
            if risk_dict[
                "human_review_required"
            ]
            else "SYSTEM_RECOMMENDATION"
        ),
        notes=notes or [],
    )

    audit_id = append_audit_record(
        audit_record
    )

    performance[
        "audit_ms"
    ] = round(
        (
            time.perf_counter()
            - t_stage
        ) * 1000,
        2,
    )

    performance[
        "total_ms"
    ] = round(
        (
            time.perf_counter()
            - t_start
        ) * 1000,
        2,
    )

    # ========================================================
    # RETURN STRUCTURED RESULT
    # ========================================================

    return {
        "question": question,

        "execution_mode": (
            "DEMO"
            if demo_mode
            else "FULL"
        ),

        "execution_config": (
            execution_config
        ),

        "performance": performance,

        # Selected jurisdiction
        "jurisdiction": jurisdiction,

        "jurisdiction_sources": {
            "selected_jurisdiction": (
                jurisdiction
            ),

            "included_jurisdictions": [
                jurisdiction,
                "International",
            ],
        },

        # Domain + intent
        "query_analysis": classification,

        # Original retrieval count
        "retrieval_candidates": len(
            results
        ),

        # Primary reranking
        "reranked_evidence": (
            reranked_results[:3]
            if demo_mode
            else reranked_results
        ),

        # Counter evidence
        "counter_evidence_query": (
            counter_evidence_query
        ),

        "counter_evidence_candidates": (
            len(counter_results)
        ),

        "counter_evidence": (
            counter_reranked_results[:2]
            if demo_mode
            else counter_reranked_results
        ),

        "counter_evidence_analysis": (
            final.get("counter_evidence", [])
        ),

        # Evidence analysis
        "evidence_analysis": (
            ranking_evidence_analysis
        ),

        # Final evidence passed downstream
        "retrieval": (
            evidence_records[:4]
            if demo_mode
            else evidence_records
        ),

        # Existing pipeline
        "classification": (
            evidence_classification
        ),

        "validation": validation,

        "evidence_assessment": (
            evidence_dict
        ),

        "absence_verification": (
            absence_dict
        ),

        "gap_analysis": gap_input,

        "risk_assessment": risk_dict,

        "final_synthesis": final,

        "claim_evidence_mappings": (
            mappings
        ),

        "governance": governance,

        "notes": notes or [],

        "audit_id": audit_id,
    }


# ============================================================
# MANUAL EXECUTION
# ============================================================

def main():

    result = run_pipeline(
        QUESTION,
        jurisdiction="India",
        demo_mode=False,
    )

    # ========================================================
    # FINAL OUTPUT
    # ========================================================

    print(
        "\n" + "=" * 80
    )

    print(
        "HACKGRID FINAL ASSESSMENT"
    )

    print(
        "=" * 80
    )

    print(
        json.dumps(
            result["final_synthesis"],
            indent=2,
            ensure_ascii=False,
        )
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "GOVERNANCE"
    )

    print(
        "=" * 80
    )

    print(
        json.dumps(
            result["risk_assessment"],
            indent=2,
            ensure_ascii=False,
        )
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "AUDIT"
    )

    print(
        "=" * 80
    )

    print(
        "Audit ID:",
        result["audit_id"],
    )

    print(
        "\nFULL ORCHESTRATOR: PASS"
    )


if __name__ == "__main__":
    main()