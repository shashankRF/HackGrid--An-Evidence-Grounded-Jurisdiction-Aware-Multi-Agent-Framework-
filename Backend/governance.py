from __future__ import annotations
"""
HackGrid Governance Layer
=========================

Deterministic governance normalization layer.

Purpose:
- Distinguish retrieved evidence from evidence that establishes a claim.
- Prevent absence of evidence from becoming proof of absence.
- Prevent unsupported policy/regulatory gap claims.
- Enforce human review for consequential regulatory decisions.
- Keep governance deterministic and independent of LLM generation.

The LLM is NOT the source of truth.
Evidence is the source of truth.
This module only applies governance rules to the pipeline outputs.
"""


from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(value: Any) -> str:
    """Safely convert any value to lowercase searchable text."""

    if value is None:
        return ""

    if isinstance(value, str):
        return value.lower()

    if isinstance(value, dict):
        return " ".join(
            f"{key} {_text(item)}"
            for key, item in value.items()
        ).lower()

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            _text(item)
            for item in value
        ).lower()

    return str(value).lower()


def _contains_any(
    text: str,
    phrases: List[str],
) -> bool:
    """Return True if any phrase occurs in text."""

    return any(
        phrase in text
        for phrase in phrases
    )


# ---------------------------------------------------------------------------
# Question-type detection
# ---------------------------------------------------------------------------

def _is_gap_establishment_question(
    question: str,
) -> bool:
    """
    Detect questions asking whether available evidence establishes
    a policy/regulatory/standards gap.
    """

    query = _text(question)

    gap_terms = [
        "policy gap",
        "regulatory gap",
        "standards gap",
        "compliance gap",
        "governance gap",
        "policy deficiency",
        "regulatory deficiency",
    ]

    establishment_terms = [
        "establish",
        "establishes",
        "established",
        "prove",
        "proves",
        "demonstrate",
        "demonstrates",
        "demonstrated",
        "show",
        "shows",
        "shown",
        "evidence",
    ]

    return (
        _contains_any(
            query,
            gap_terms,
        )
        and _contains_any(
            query,
            establishment_terms,
        )
    )


def _is_absence_question(
    question: str,
) -> bool:
    """
    Detect questions asking whether something does not exist.

    Example:
    'Does the KB prove India has no regulation...'
    """

    query = _text(question)

    absence_terms = [
        "no regulation",
        "no regulations",
        "no policy",
        "no policies",
        "no requirement",
        "no requirements",
        "no provision",
        "no provisions",
        "does not exist",
        "do not exist",
        "doesn't exist",
        "don't exist",
        "not exist",
        "none exists",
        "nothing exists",
        "prove there is no",
        "prove there are no",
        "prove no",
    ]

    return _contains_any(
        query,
        absence_terms,
    )


def _is_consequential_auto_approval_question(
    question: str,
) -> bool:
    """
    Detect high-consequence questions asking whether AI should
    automatically approve or authorize a decision.
    """

    query = _text(question)

    consequence_terms = [
        "consequential",
        "high impact",
        "high-impact",
        "critical",
        "regulatory decision",
        "compliance decision",
        "security decision",
        "safety decision",
        "operational decision",
    ]

    automation_terms = [
        "automatically approve",
        "auto approve",
        "auto-approve",
        "automatically approved",
        "approve automatically",
        "automated approval",
        "ai approval",
        "ai approve",
        "ai automatically",
    ]

    return (
        _contains_any(
            query,
            consequence_terms,
        )
        and _contains_any(
            query,
            automation_terms,
        )
    )


# ---------------------------------------------------------------------------
# Final synthesis helpers
# ---------------------------------------------------------------------------

def _final_claim_status(
    final_synthesis: Dict[str, Any],
) -> str:
    """
    Safely extract the first final-claim status.
    """

    if not isinstance(
        final_synthesis,
        dict,
    ):
        return ""

    claims = final_synthesis.get(
        "claims",
        [],
    )

    if not isinstance(
        claims,
        list,
    ) or not claims:
        return ""

    first_claim = claims[0]

    if not isinstance(
        first_claim,
        dict,
    ):
        return ""

    return str(
        first_claim.get(
            "status",
            "",
        )
    ).upper()


def _evidence_has_positive_gap_support(
    classification: Any,
    final_synthesis: Dict[str, Any],
) -> bool:
    """
    Conservative test for explicit positive evidence of a policy gap.

    We only return True if the available structured/LLM output explicitly
    indicates supporting evidence for the existence of a gap.

    Everything else is treated conservatively as NOT established.
    """

    combined = _text(
        classification
    )

    positive_gap_phrases = [
        "policy gap exists",
        "policy gap is established",
        "gap is established",
        "regulatory gap exists",
        "regulatory gap is established",
        "standards gap exists",
        "gap demonstrated",
        "gap is demonstrated",
        "positive evidence of a policy gap",
        "supporting evidence for a policy gap",
    ]

    if _contains_any(
        combined,
        positive_gap_phrases,
    ):
        return True

    claims = final_synthesis.get(
        "claims",
        [],
    )

    if isinstance(
        claims,
        list,
    ):

        for claim in claims:

            if not isinstance(
                claim,
                dict,
            ):
                continue

            status = str(
                claim.get(
                    "status",
                    "",
                )
            ).upper()

            claim_text = _text(
                claim.get(
                    "claim",
                    "",
                )
            )

            if status in {
                "SUPPORTED",
                "ESTABLISHED",
                "SUFFICIENT",
            }:

                if _contains_any(
                    claim_text,
                    [
                        "policy gap exists",
                        "regulatory gap exists",
                        "standards gap exists",
                        "policy gap is established",
                        "regulatory gap is established",
                    ],
                ):
                    return True

    return False


# ---------------------------------------------------------------------------
# Main governance function
# ---------------------------------------------------------------------------

def evaluate_governance(
    question: str,
    evidence_assessment: Dict[str, Any] | None = None,
    gap_analysis: Dict[str, Any] | None = None,
    risk_assessment: Dict[str, Any] | None = None,
    final_synthesis: Dict[str, Any] | None = None,
    classification: Any = None,
) -> Dict[str, Any]:
    """
    Apply deterministic governance rules to the pipeline output.
    """

    evidence_assessment = (
        evidence_assessment
        if evidence_assessment is not None
        else {}
    )

    gap_analysis = (
        gap_analysis
        if gap_analysis is not None
        else {}
    )

    risk_assessment = (
        risk_assessment
        if risk_assessment is not None
        else {}
    )

    final_synthesis = (
        final_synthesis
        if final_synthesis is not None
        else {}
    )

    # -----------------------------------------------------------------------
    # Normalize incoming status fields
    # -----------------------------------------------------------------------

    original_evidence_status = str(
        evidence_assessment.get(
            "overall_status",
            "UNKNOWN",
        )
    ).upper()

    original_gap_status = str(
        gap_analysis.get(
            "overall_status",
            "UNKNOWN",
        )
    ).upper()

    risk_level = str(
        risk_assessment.get(
            "risk_level",
            "UNKNOWN",
        )
    ).upper()

    human_review = bool(
        risk_assessment.get(
            "human_review_required",
            False,
        )
    )

    escalation = str(
        risk_assessment.get(
            "escalation_level",
            "",
        )
    ).upper()

    final_claim_status = _final_claim_status(
        final_synthesis
    )

    # -----------------------------------------------------------------------
    # Default governance state
    # -----------------------------------------------------------------------

    result = {
        "status": "ASSESSMENT_REQUIRES_REVIEW",
        "evidence_status": original_evidence_status,
        "gap_status": original_gap_status,
        "risk_level": risk_level,
        "human_review_required": human_review,
        "escalation_level": escalation,
        "reason": (
            "Governance status derived from evidence, risk, "
            "and decision context."
        ),
        "rule": "DEFAULT_GOVERNANCE",
    }

    # -----------------------------------------------------------------------
    # RULE 1 — Explicit regulatory/policy absence
    #
    # Absence of retrieved evidence MUST NOT become proof of absence.
    # -----------------------------------------------------------------------

    if _is_absence_question(
        question
    ):

        result.update({
            "status": "REGULATORY_ABSENCE_NOT_ESTABLISHED",
            "evidence_status": "INSUFFICIENT",
            "gap_status": "ABSENCE_NOT_ESTABLISHED",
            "human_review_required": True,
            "escalation_level": (
                escalation
                or "SENIOR_AUTHORITY"
            ),
            "reason": (
                "The available evidence does not establish that the "
                "regulation, policy, requirement, or provision does not "
                "exist. Absence of retrieved evidence is not proof "
                "of absence."
            ),
            "rule": "ABSENCE_NOT_ESTABLISHED",
        })

        return result

    # -----------------------------------------------------------------------
    # RULE 2 — Policy/regulatory gap establishment
    #
    # A gap must be positively established by evidence.
    # Retrieval alone is not sufficient.
    #
    # CRITICAL GOVERNANCE RULE:
    #
    # If final synthesis says the claim is CONTRADICTED or INSUFFICIENT,
    # governance MUST NOT override it and declare the gap established.
    # -----------------------------------------------------------------------

    if _is_gap_establishment_question(
        question
    ):

        # ---------------------------------------------------------------
        # HARD GUARD AGAINST CONTRADICTORY FINAL CLAIMS
        # ---------------------------------------------------------------

        if final_claim_status in {
            "CONTRADICTED",
            "INSUFFICIENT",
        }:

            result.update({
                "status": "POLICY_GAP_NOT_ESTABLISHED",
                "evidence_status": "INSUFFICIENT",
                "gap_status": "ABSENCE_NOT_ESTABLISHED",
                "human_review_required": True,
                "escalation_level": (
                    escalation
                    or "SENIOR_AUTHORITY"
                ),
                "reason": (
                    "The final evidence assessment does not establish "
                    "the existence of a policy, regulatory, standards, "
                    "or governance gap."
                ),
                "rule": "POLICY_GAP_NOT_ESTABLISHED",
            })

            return result

        # ---------------------------------------------------------------
        # Check for explicit positive gap support
        # ---------------------------------------------------------------

        positive_gap_support = (
            _evidence_has_positive_gap_support(
                classification=classification,
                final_synthesis=final_synthesis,
            )
        )

        # ---------------------------------------------------------------
        # No positive support
        # ---------------------------------------------------------------

        if not positive_gap_support:

            result.update({
                "status": "POLICY_GAP_NOT_ESTABLISHED",
                "evidence_status": "INSUFFICIENT",
                "gap_status": "ABSENCE_NOT_ESTABLISHED",
                "human_review_required": True,
                "escalation_level": (
                    escalation
                    or "SENIOR_AUTHORITY"
                ),
                "reason": (
                    "The available evidence does not establish the "
                    "existence of a policy, regulatory, standards, "
                    "or governance gap."
                ),
                "rule": "POLICY_GAP_NOT_ESTABLISHED",
            })

            return result

        # ---------------------------------------------------------------
        # Positive gap support
        #
        # This branch is reachable only when the final claim is not
        # CONTRADICTED or INSUFFICIENT and explicit positive support exists.
        # ---------------------------------------------------------------

        result.update({
            "status": "POLICY_GAP_ESTABLISHED",
            "evidence_status": "SUFFICIENT",
            "gap_status": "SUFFICIENT",
            "reason": (
                "Available evidence explicitly supports the existence "
                "of the identified policy/regulatory gap."
            ),
            "rule": "POLICY_GAP_ESTABLISHED",
        })

        return result

    # -----------------------------------------------------------------------
    # RULE 3 — Consequential AI auto-approval
    #
    # AI must not automatically approve consequential regulatory decisions.
    # -----------------------------------------------------------------------

    if _is_consequential_auto_approval_question(
        question
    ):

        normalized_evidence_status = (
            "INSUFFICIENT"
            if original_evidence_status in {
                "UNKNOWN",
                "INSUFFICIENT",
                "ABSENCE_NOT_ESTABLISHED",
            }
            else original_evidence_status
        )

        normalized_gap_status = (
            original_gap_status
            if original_gap_status != "UNKNOWN"
            else "INSUFFICIENT"
        )

        result.update({
            "status": "HUMAN_REVIEW_REQUIRED",
            "evidence_status": normalized_evidence_status,
            "gap_status": normalized_gap_status,
            "risk_level": "CRITICAL",
            "human_review_required": True,
            "escalation_level": "SENIOR_AUTHORITY",
            "reason": (
                "A consequential telecom compliance decision must not "
                "be automatically approved by AI. Human authority "
                "is required."
            ),
            "rule": "CONSEQUENTIAL_DECISION_HUMAN_REVIEW",
        })

        return result

    # -----------------------------------------------------------------------
    # GENERAL FALLBACK
    # -----------------------------------------------------------------------

    if risk_level == "CRITICAL":

        result["human_review_required"] = True

        if not result["escalation_level"]:
            result["escalation_level"] = (
                "SENIOR_AUTHORITY"
            )

        result["status"] = (
            "HUMAN_REVIEW_REQUIRED"
        )

        result["rule"] = (
            "CRITICAL_RISK_HUMAN_REVIEW"
        )

    return result


# ---------------------------------------------------------------------------
# Utility: merge governance into pipeline output
# ---------------------------------------------------------------------------

def apply_governance_to_pipeline(
    pipeline_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply governance to an existing pipeline result.

    This function does not mutate the original evidence/RAG objects.
    It adds a top-level governance object and exposes normalized
    governance status.
    """

    governance = evaluate_governance(
        question=pipeline_result.get(
            "question",
            "",
        ),
        evidence_assessment=pipeline_result.get(
            "evidence_assessment",
            {},
        ),
        gap_analysis=pipeline_result.get(
            "gap_analysis",
            {},
        ),
        risk_assessment=pipeline_result.get(
            "risk_assessment",
            {},
        ),
        final_synthesis=pipeline_result.get(
            "final_synthesis",
            {},
        ),
        classification=pipeline_result.get(
            "classification",
        ),
    )

    pipeline_result["governance"] = governance

    return pipeline_result