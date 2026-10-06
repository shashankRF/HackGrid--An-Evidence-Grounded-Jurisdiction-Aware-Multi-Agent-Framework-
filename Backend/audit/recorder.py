from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


AUDIT_DIR = (
    Path(__file__).resolve().parent
    / "records"
)

AUDIT_FILE = AUDIT_DIR / "audit.jsonl"

PIPELINE_VERSION = "hackgrid-evidence-pipeline-v1"


def _canonical_json(data: Dict[str, Any]) -> str:

    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def generate_audit_id(
    record: Dict[str, Any],
) -> str:

    canonical = _canonical_json(record)

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    return f"AUD-{digest[:24]}"


def create_audit_record(
    *,
    question: str,
    model: str,
    retrieved_evidence: List[Dict[str, Any]],
    evidence_classification: Dict[str, Any],
    evidence_assessment: Dict[str, Any],
    absence_verification: List[Dict[str, Any]],
    gap_analysis: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    final_synthesis: Dict[str, Any],
    claim_evidence_mappings: List[Dict[str, Any]],
    human_review_required: bool,
    human_reviewer: str = "",
    human_action: str = "",
    reviewer_modifications: str = "",
    final_decision: str = "",
    notes: List[str] | None = None,
) -> Dict[str, Any]:

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    record = {
        "timestamp": timestamp,
        "question": question,
        "pipeline_version": PIPELINE_VERSION,
        "model": model,
        "retrieved_evidence": retrieved_evidence,
        "evidence_classification": evidence_classification,
        "evidence_assessment": evidence_assessment,
        "absence_verification": absence_verification,
        "gap_analysis": gap_analysis,
        "risk_assessment": risk_assessment,
        "final_synthesis": final_synthesis,
        "claim_evidence_mappings": (
            claim_evidence_mappings
        ),
        "human_review_required": (
            human_review_required
        ),
        "human_reviewer": human_reviewer,
        "human_action": human_action,
        "reviewer_modifications": (
            reviewer_modifications
        ),
        "final_decision": final_decision,
        "notes": notes or [],
    }

    record["audit_id"] = generate_audit_id(
        record
    )

    return record


def append_audit_record(
    record: Dict[str, Any],
) -> str:

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with AUDIT_FILE.open(
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                default=str,
            )
        )

        file.write("\n")

    return record["audit_id"]


def load_audit_records() -> List[Dict[str, Any]]:

    if not AUDIT_FILE.exists():
        return []

    records = []

    with AUDIT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            records.append(
                json.loads(line)
            )

    return records