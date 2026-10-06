from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
from dotenv import load_dotenv

load_dotenv()
import json
import os
import re
from typing import Any, Dict, List

from groq import Groq


# ============================================================
# CONFIGURATION
# ============================================================

GROQ_MODEL = "openai/gpt-oss-120b"

MAX_EVIDENCE_ITEMS = 8
MAX_EVIDENCE_CHARS = 1800

MAX_CLASSIFICATION_CHARS = 2500
MAX_GAP_CHARS = 2500
MAX_RISK_CHARS = 1800
MAX_ABSENCE_CHARS = 1800

MAX_PROMPT_CHARS = 27000

SYNTHESIS_MAX_TOKENS = 3000


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are HackGrid's final evidence-grounded assessment engine.

Your job is to produce a precise, conservative assessment from the
supplied evidence and structured analysis.

CORE RULES:

1. Evidence is the source of truth.
2. Do not invent facts, regulations, standards, clauses, pages,
   organizations, deployments, or technical requirements.
3. Every important factual claim must reference one or more supplied
   evidence IDs.
4. Preserve uncertainty when evidence is insufficient.
5. Absence of retrieved evidence is NOT proof that something does not
   exist.
6. Distinguish:
   - Supporting Evidence
   - Contradicting Evidence
   - Contextual Evidence
   - Evidence Gaps
7. Do not convert an evidence gap into a confirmed regulatory or
   policy gap.
8. Distinguish mandatory requirements from advisory guidance.
9. Do not override human-review or governance requirements.
10. Risk and authority decisions are determined by the supplied
    governance/risk assessment, not by you.
11. Do not claim exhaustive legal or standards coverage unless the
    supplied evidence explicitly establishes that.
12. If evidence conflicts, explicitly preserve the conflict.
13. If evidence is insufficient, say so clearly.
14. Keep recommendations grounded in the evidence and limitations.

Return ONLY valid JSON.

Required JSON structure:

{
  "assessment": "string",
  "claims": [
    {
      "claim_id": "CLAIM-001",
      "claim": "string",
      "status": "SUPPORTED | CONTRADICTED | PARTIALLY_SUPPORTED | INSUFFICIENT",
      "evidence_ids": ["EV-001"],
      "confidence": 0.0
    }
  ],
  "technical_implications": [],
  "regulatory_implications": [],
  "gaps": [],
  "recommended_actions": [],
  "limitations": [],
  "human_review_required": true,
  "governance_note": "string",
  "model": "openai/gpt-oss-120b",
  "status": "SUCCESS"
}
"""


# ============================================================
# CLIENT
# ============================================================

def _get_client() -> Groq:

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    return Groq(
        api_key=api_key
    )


# ============================================================
# TEXT COMPACTION
# ============================================================

def _compact_text(
    text: Any,
    max_chars: int,
) -> str:

    if text is None:
        return ""

    text = str(text).strip()

    if len(text) <= max_chars:
        return text

    return (
        text[:max_chars]
        + "\n[Evidence text truncated for synthesis.]"
    )


# ============================================================
# EVIDENCE COMPACTION
# ============================================================

def _compact_evidence(
    evidence_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    compact = []

    for index, item in enumerate(
        evidence_records[:MAX_EVIDENCE_ITEMS],
        start=1,
    ):

        metadata = item.get(
            "metadata",
            {},
        )

        compact_metadata = {}

        # Preserve the most important provenance fields.
        for key in [
            "document",
            "source_file",
            "folder",
            "jurisdiction",
            "document_type",
            "page",
            "section",
            "clause",
            "chunk_id",
            "language",
        ]:

            if key in metadata:
                compact_metadata[key] = metadata[key]

        evidence_id = (
            item.get("evidence_id")
            or metadata.get("evidence_id")
            or f"EV-{index:03d}"
        )

        compact.append(
            {
                "evidence_id": evidence_id,
                "text": _compact_text(
                    item.get("text", ""),
                    MAX_EVIDENCE_CHARS,
                ),
                "metadata": compact_metadata,
                "role": item.get(
                    "role",
                    "Contextual Evidence",
                ),
                "role_confidence": item.get(
                    "role_confidence",
                    0.0,
                ),
                "reranker_score": item.get(
                    "reranker_score"
                ),
            }
        )

    return compact


# ============================================================
# GENERIC OBJECT COMPACTION
# ============================================================

def _compact_object(
    value: Any,
    max_chars: int,
) -> Any:

    if value is None:
        return None

    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except Exception:
        serialized = str(value)

    if len(serialized) <= max_chars:
        return value

    return (
        serialized[:max_chars]
        + "\n[Context truncated for synthesis.]"
    )


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json(
    text: str,
) -> Dict[str, Any]:

    if not text:
        raise ValueError(
            "GPT-OSS returned an empty response."
        )

    text = text.strip()

    # Direct JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown JSON block.
    fenced = re.search(
        r"```(?:json)?\s*(\{.*\})\s*```",
        text,
        flags=re.DOTALL,
    )

    if fenced:

        try:
            return json.loads(
                fenced.group(1)
            )
        except json.JSONDecodeError:
            pass

    # Find first JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        candidate = text[
            start:end + 1
        ]

        try:
            return json.loads(
                candidate
            )
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Could not extract valid JSON from GPT-OSS response."
    )


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def _validate_output(
    result: Dict[str, Any],
) -> Dict[str, Any]:

    required_fields = [
        "assessment",
        "claims",
        "technical_implications",
        "regulatory_implications",
        "gaps",
        "recommended_actions",
        "limitations",
        "human_review_required",
        "governance_note",
        "model",
        "status",
    ]

    for field in required_fields:

        if field not in result:
            raise ValueError(
                f"Missing synthesis field: {field}"
            )

    if not isinstance(
        result["claims"],
        list,
    ):
        raise ValueError(
            "claims must be a list."
        )

    for claim in result["claims"]:

        if not isinstance(
            claim,
            dict,
        ):
            raise ValueError(
                "Each claim must be an object."
            )

        for field in [
            "claim_id",
            "claim",
            "status",
            "evidence_ids",
            "confidence",
        ]:

            if field not in claim:
                raise ValueError(
                    f"Claim missing field: {field}"
                )

        if not isinstance(
            claim["evidence_ids"],
            list,
        ):
            raise ValueError(
                "claim evidence_ids must be a list."
            )

        if not 0.0 <= float(
            claim["confidence"]
        ) <= 1.0:

            raise ValueError(
                "Claim confidence must be between 0 and 1."
            )

    result["model"] = GROQ_MODEL
    result["status"] = "SUCCESS"

    return result


# ============================================================
# SYNTHESIS PROMPT
# ============================================================

def build_synthesis_prompt(
    question: str,
    evidence_records: List[Dict[str, Any]],
    classification: Dict[str, Any],
    evidence_assessment: Dict[str, Any],
    absence_verifications: List[Dict[str, Any]],
    gap_input: Dict[str, Any],
    risk_assessment: Dict[str, Any],
) -> str:

    compact_evidence = _compact_evidence(
        evidence_records
    )

    compact_classification = (
        _compact_object(
            classification,
            MAX_CLASSIFICATION_CHARS,
        )
    )

    compact_evidence_assessment = (
        _compact_object(
            evidence_assessment,
            1800,
        )
    )

    compact_absence = (
        _compact_object(
            absence_verifications,
            MAX_ABSENCE_CHARS,
        )
    )

    compact_gap = (
        _compact_object(
            gap_input,
            MAX_GAP_CHARS,
        )
    )

    compact_risk = (
        _compact_object(
            risk_assessment,
            MAX_RISK_CHARS,
        )
    )

    prompt = f"""
QUESTION:
{question}

DOMAIN / INTENT CLASSIFICATION:
{json.dumps(
    compact_classification,
    ensure_ascii=False,
    indent=2,
)}

EVIDENCE:
{json.dumps(
    compact_evidence,
    ensure_ascii=False,
    indent=2,
)}

EVIDENCE ASSESSMENT:
{json.dumps(
    compact_evidence_assessment,
    ensure_ascii=False,
    indent=2,
)}

ABSENCE VERIFICATION:
{json.dumps(
    compact_absence,
    ensure_ascii=False,
    indent=2,
)}

GAP ANALYSIS:
{json.dumps(
    compact_gap,
    ensure_ascii=False,
    indent=2,
)}

RISK / GOVERNANCE:
{json.dumps(
    compact_risk,
    ensure_ascii=False,
    indent=2,
)}

Produce the final evidence-grounded assessment.

Remember:
- Use only supplied evidence.
- Cite evidence IDs for substantive claims.
- Do not invent sources or regulations.
- Do not treat absence of evidence as proof of absence.
- Preserve contradictions and uncertainty.
- Never override the supplied human-review requirement.
"""

    # Final emergency character cap.
    if len(prompt) > MAX_PROMPT_CHARS:

        prompt = (
            prompt[:MAX_PROMPT_CHARS]
            + "\n[Prompt context compacted.]"
        )

    return prompt


# ============================================================
# FINAL SYNTHESIS
# ============================================================

def synthesize_final_assessment(
    question: str,
    evidence_records: List[Dict[str, Any]],
    classification: Dict[str, Any],
    evidence_assessment: Dict[str, Any],
    absence_verifications: List[Dict[str, Any]],
    gap_input: Dict[str, Any],
    risk_assessment: Dict[str, Any],
) -> Dict[str, Any]:

    client = _get_client()

    user_prompt = build_synthesis_prompt(
        question=question,
        evidence_records=evidence_records,
        classification=classification,
        evidence_assessment=evidence_assessment,
        absence_verifications=absence_verifications,
        gap_input=gap_input,
        risk_assessment=risk_assessment,
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        temperature=0.1,

        max_tokens=SYNTHESIS_MAX_TOKENS,
    )

    content = (
        response.choices[0]
        .message
        .content
    )

    result = _extract_json(
        content
    )

    return _validate_output(
        result
    )