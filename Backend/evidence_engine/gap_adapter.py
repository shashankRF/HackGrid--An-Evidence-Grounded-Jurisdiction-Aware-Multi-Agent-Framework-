from __future__ import annotations
"""
HackGrid Gap Analysis Adapter
=============================

Converts Evidence Engine output into the gap-analysis representation.

Governance principles:
- Evidence retrieval != proof of a claim.
- Absence of retrieved evidence != proof of absence.
- Policy/regulatory gaps must not be declared without supporting evidence.
"""


from dataclasses import asdict, is_dataclass
from typing import Any, Dict


ABSENCE_PHRASES = (
    "no regulation",
    "no regulations",
    "no policy",
    "no policies",
    "no requirement",
    "no requirements",
    "no provision",
    "no provisions",
    "no standard",
    "no standards",
    "no rule",
    "no rules",
    "does not exist",
    "do not exist",
    "doesn't exist",
    "don't exist",
    "not exist",
    "no evidence of existence",
    "prove no",
    "proves no",
    "proven absent",
    "absence of",
)


def _to_dict(value: Any) -> Dict[str, Any]:
    """
    Convert EvidenceAssessment dataclass or dictionary
    into a dictionary.
    """

    if isinstance(value, dict):
        return value

    if is_dataclass(value):
        return asdict(value)

    if hasattr(value, "__dict__"):
        return dict(vars(value))

    return {}


def _text(value: Any) -> str:
    """
    Safely convert arbitrary values to lowercase text.
    """

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


def _explicit_absence_claim(question: str) -> bool:
    """
    Detect explicit questions about absence or non-existence.
    """

    query = _text(question)

    return any(
        phrase in query
        for phrase in ABSENCE_PHRASES
    )


def _absence_was_not_established(
    absence_verifications: list,
) -> bool:
    """
    Return True only when an ABSENCE_NOT_ESTABLISHED
    verification belongs to an actual absence/non-existence claim.

    A generic verification status alone must NOT convert a
    normal decision question into an absence claim.
    """

    for verification in absence_verifications:

        if not isinstance(verification, dict):
            continue

        verification_status = str(
            verification.get(
                "verification_status",
                "",
            )
        ).upper()

        if verification_status != "ABSENCE_NOT_ESTABLISHED":
            continue

        claim = str(
            verification.get(
                "claim",
                "",
            )
        )

        if _explicit_absence_claim(claim):
            return True

    return False


def build_gap_input(
    evidence_assessment: Any,
    absence_verifications: list | None = None,
    question: str = "",
) -> Dict[str, Any]:
    """
    Build the structured gap-analysis input.

    EvidenceAssessment may be either:
    - the EvidenceAssessment dataclass, or
    - a dictionary.
    """

    # ---------------------------------------------------------------
    # Normalize inputs
    # ---------------------------------------------------------------

    absence_verifications = (
        absence_verifications
        if absence_verifications is not None
        else []
    )

    evidence = _to_dict(evidence_assessment)

    # ---------------------------------------------------------------
    # Evidence status
    # ---------------------------------------------------------------

    evidence_status = str(
        evidence.get(
            "overall_status",
            "SUFFICIENT",
        )
    ).upper()

    # ---------------------------------------------------------------
    # Missing evidence
    # ---------------------------------------------------------------

    missing_evidence = list(
        evidence.get(
            "missing_evidence",
            [],
        )
        or []
    )

    # ---------------------------------------------------------------
    # Explicit absence detection
    #
    # Either:
    # 1. The question itself explicitly asks about absence, OR
    # 2. An absence verification is attached to an actual
    #    absence/non-existence claim.
    # ---------------------------------------------------------------

    explicit_absence = _explicit_absence_claim(
        question
    )

    verified_absence_uncertainty = (
        _absence_was_not_established(
            absence_verifications
        )
    )

    if (
        explicit_absence
        or verified_absence_uncertainty
    ):

        if (
            "ABSENCE_NOT_ESTABLISHED"
            not in missing_evidence
        ):
            missing_evidence.append(
                "ABSENCE_NOT_ESTABLISHED"
            )

        return {
            "overall_status": (
                "ABSENCE_NOT_ESTABLISHED"
            ),
            "evidence_status": evidence_status,
            "missing_evidence": missing_evidence,
            "absence_verifications": (
                absence_verifications
            ),
            "reason": (
                "The available evidence does not establish "
                "that the relevant regulation, policy, "
                "requirement, provision, or standard "
                "does not exist."
            ),
            "governance_note": (
                "Absence of retrieved evidence is not "
                "proof of absence."
            ),
        }

    # ---------------------------------------------------------------
    # Normal gap analysis
    # ---------------------------------------------------------------

    return {
        "overall_status": evidence_status,
        "evidence_status": evidence_status,
        "missing_evidence": missing_evidence,
        "absence_verifications": (
            absence_verifications
        ),
        "reason": (
            "Gap status follows the Evidence Engine "
            "assessment. No unsupported absence conclusion "
            "is made."
        ),
        "governance_note": (
            "A policy or regulatory gap must be established "
            "by appropriate supporting evidence."
        ),
    }