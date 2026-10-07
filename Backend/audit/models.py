from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AuditRecord:

    audit_id: str

    timestamp: str

    question: str

    pipeline_version: str

    model: str

    retrieved_evidence: List[Dict[str, Any]] = field(
        default_factory=list
    )

    evidence_classification: Dict[str, Any] = field(
        default_factory=dict
    )

    evidence_assessment: Dict[str, Any] = field(
        default_factory=dict
    )

    absence_verification: List[Dict[str, Any]] = field(
        default_factory=list
    )

    gap_analysis: Dict[str, Any] = field(
        default_factory=dict
    )

    risk_assessment: Dict[str, Any] = field(
        default_factory=dict
    )

    final_synthesis: Dict[str, Any] = field(
        default_factory=dict
    )

    claim_evidence_mappings: List[Dict[str, Any]] = field(
        default_factory=list
    )

    human_review_required: bool = False

    human_reviewer: str = ""

    human_action: str = ""

    reviewer_modifications: str = ""

    final_decision: str = ""

    notes: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:

        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "question": self.question,
            "pipeline_version": self.pipeline_version,
            "model": self.model,
            "retrieved_evidence": self.retrieved_evidence,
            "evidence_classification": self.evidence_classification,
            "evidence_assessment": self.evidence_assessment,
            "absence_verification": self.absence_verification,
            "gap_analysis": self.gap_analysis,
            "risk_assessment": self.risk_assessment,
            "final_synthesis": self.final_synthesis,
            "claim_evidence_mappings": (
                self.claim_evidence_mappings
            ),
            "human_review_required": (
                self.human_review_required
            ),
            "human_reviewer": self.human_reviewer,
            "human_action": self.human_action,
            "reviewer_modifications": (
                self.reviewer_modifications
            ),
            "final_decision": self.final_decision,
            "notes": self.notes,
        }


@dataclass
class ReviewEvent:

    audit_id: str

    timestamp: str

    human_action: str

    final_decision: str

    reviewer: str = "Human reviewer"

    reviewer_modifications: str | None = None

    reviewer_reason: str | None = None

    def to_dict(self) -> Dict[str, Any]:

        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "human_action": self.human_action,
            "final_decision": self.final_decision,
            "reviewer": self.reviewer,
            "reviewer_modifications": self.reviewer_modifications,
            "reviewer_reason": self.reviewer_reason,
        }