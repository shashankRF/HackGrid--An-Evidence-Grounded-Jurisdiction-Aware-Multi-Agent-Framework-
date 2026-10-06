from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .audit.recorder import load_audit_records
from .demo_scenarios.library import get_scenarios


router = APIRouter(
    prefix="/api/audits",
    tags=["Audit Trail"],
)


def _build_scenario_map() -> Dict[str, Dict[str, Any]]:
    scenario_map = {}
    for s in get_scenarios():
        for st in s.get("steps", []):
            prompt = st.get("evidence_prompt", "").strip()
            scenario_map[prompt] = {
                "scenario_id": s.get("scenario_id"),
                "scenario_title": s.get("title"),
                "domain": s.get("domain"),
                "step_id": st.get("step_id"),
                "step_title": st.get("title"),
                "simulated": True,
            }
    return scenario_map


def enrich_audit_record(r: Dict[str, Any], scenario_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    q = (r.get("question") or "").strip()
    sc = scenario_map.get(q)

    # Domain
    domain = None
    if sc:
        domain = sc["domain"]
    elif "evidence_classification" in r and isinstance(r["evidence_classification"], dict):
        domain = r["evidence_classification"].get("domain")

    if not domain:
        q_lower = q.lower()
        if any(w in q_lower for w in ["vessel", "maritime", "ais", "gnss", "imo"]):
            domain = "Maritime"
        elif any(w in q_lower for w in ["5g", "slicing", "telecom", "3gpp", "core", "6g"]):
            domain = "Telecom / 5G"
        elif any(w in q_lower for w in ["uav", "tactical", "datalink", "defence", "military"]):
            domain = "Defence"
        elif any(w in q_lower for w in ["policy", "regulation", "compliance", "dpdp", "trai", "dot", "act"]):
            domain = "Policy / Compliance"
        else:
            domain = "General Evidence"

    # Jurisdiction
    jur = "India"
    retrieved = r.get("retrieved_evidence") or []
    for ev in retrieved:
        if isinstance(ev, dict):
            j = ev.get("jurisdiction") or (
                ev.get("metadata", {}).get("jurisdiction")
                if isinstance(ev.get("metadata"), dict)
                else None
            )
            if j:
                jur = j
                break
    if "european union" in q.lower() or " eu " in q.lower():
        jur = "European Union"
    elif "india" in q.lower():
        jur = "India"

    # Type
    audit_type = "SIMULATED SCENARIO" if sc else "QUESTION / ANALYSIS"

    # Risk
    risk_info = r.get("risk_assessment") or {}
    risk_level = risk_info.get("risk_level", "MODERATE")
    risk_score = risk_info.get("risk_score", 50)

    # Evidence Status
    ev_ass = r.get("evidence_assessment") or {}
    evidence_status = ev_ass.get("overall_status", "SUFFICIENT")

    # Human Review
    human_review = r.get("human_review_required", False)
    if risk_info.get("human_review_required"):
        human_review = True

    # Synthesis excerpt
    synth = r.get("final_synthesis") or {}
    gap = r.get("gap_analysis") or {}
    assessment = synth.get("assessment") or gap.get("verdict") or "Analysis completed."

    return {
        "audit_id": r.get("audit_id"),
        "timestamp": r.get("timestamp"),
        "question": q,
        "audit_type": audit_type,
        "domain": domain,
        "jurisdiction": jur,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "evidence_status": evidence_status,
        "human_review_required": human_review,
        "final_decision": r.get("final_decision", "PENDING_HUMAN_REVIEW"),
        "evidence_count": len(retrieved),
        "claims_count": len(synth.get("claims") or r.get("claim_evidence_mappings") or []),
        "assessment_excerpt": str(assessment)[:180],
        "scenario": sc,
    }


@router.get("")
def get_all_audits(
    search: Optional[str] = Query(None, description="Search term across question, audit_id, domain, assessment"),
    domain: Optional[str] = Query(None, description="Filter by domain category"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    evidence_status: Optional[str] = Query(None, description="Filter by evidence status"),
    human_review_required: Optional[bool] = Query(None, description="Filter by human review requirement"),
    audit_type: Optional[str] = Query(None, description="Filter by audit type"),
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    sort: Optional[str] = Query("newest", description="Sort order: newest, oldest, highest_risk, lowest_risk"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    raw_records = load_audit_records()
    scenario_map = _build_scenario_map()

    enriched = [enrich_audit_record(r, scenario_map) for r in raw_records]

    # Calculate real overview metrics
    total_audits = len(enriched)
    critical_cases = sum(1 for a in enriched if str(a["risk_level"]).upper() == "CRITICAL")
    human_review_count = sum(1 for a in enriched if a["human_review_required"])
    simulated_count = sum(1 for a in enriched if a["audit_type"] == "SIMULATED SCENARIO")
    insufficient_count = sum(1 for a in enriched if str(a["evidence_status"]).upper() in ["INSUFFICIENT", "MISSING"])

    domain_counts: Dict[str, int] = {}
    jur_counts: Dict[str, int] = {}
    for a in enriched:
        d = a["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
        j = a["jurisdiction"]
        jur_counts[j] = jur_counts.get(j, 0) + 1

    # Filter
    filtered = enriched

    if search:
        s_term = search.strip().lower()
        filtered = [
            a for a in filtered
            if s_term in a["audit_id"].lower()
            or s_term in a["question"].lower()
            or s_term in a["domain"].lower()
            or s_term in a["jurisdiction"].lower()
            or s_term in a["assessment_excerpt"].lower()
            or (a["scenario"] and s_term in a["scenario"]["scenario_title"].lower())
            or (a["scenario"] and s_term in a["scenario"]["scenario_id"].lower())
        ]

    if domain and domain.lower() != "all":
        filtered = [a for a in filtered if a["domain"].lower() == domain.lower()]

    if jurisdiction and jurisdiction.lower() != "all":
        filtered = [a for a in filtered if a["jurisdiction"].lower() == jurisdiction.lower()]

    if risk_level and risk_level.lower() != "all":
        filtered = [a for a in filtered if str(a["risk_level"]).lower() == risk_level.lower()]

    if evidence_status and evidence_status.lower() != "all":
        filtered = [a for a in filtered if str(a["evidence_status"]).lower() == evidence_status.lower()]

    if human_review_required is not None:
        filtered = [a for a in filtered if a["human_review_required"] == human_review_required]

    if audit_type and audit_type.lower() != "all":
        filtered = [a for a in filtered if a["audit_type"].lower() == audit_type.lower()]

    if scenario_id:
        filtered = [
            a for a in filtered
            if a["scenario"] and a["scenario"]["scenario_id"].lower() == scenario_id.lower()
        ]

    # Sort
    if sort == "oldest":
        filtered.sort(key=lambda x: x["timestamp"] or "")
    elif sort == "highest_risk":
        filtered.sort(key=lambda x: x["risk_score"], reverse=True)
    elif sort == "lowest_risk":
        filtered.sort(key=lambda x: x["risk_score"])
    else:  # newest default
        filtered.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    paginated = filtered[offset : offset + limit]

    return {
        "total": total_audits,
        "filtered_count": len(filtered),
        "offset": offset,
        "limit": limit,
        "metrics": {
            "total_audits": total_audits,
            "critical_cases": critical_cases,
            "human_review_required": human_review_count,
            "simulated_scenarios": simulated_count,
            "insufficient_evidence": insufficient_count,
            "domains": domain_counts,
            "jurisdictions": jur_counts,
        },
        "audits": paginated,
    }


@router.get("/{audit_id}")
def get_audit_detail(audit_id: str):
    raw_records = load_audit_records()
    target_record = None
    for r in raw_records:
        if r.get("audit_id") == audit_id:
            target_record = r
            break

    if target_record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Audit record '{audit_id}' not found.",
        )

    scenario_map = _build_scenario_map()
    enriched_summary = enrich_audit_record(target_record, scenario_map)

    full_payload = dict(target_record)
    full_payload["scenario"] = enriched_summary.get("scenario")
    full_payload["domain"] = enriched_summary.get("domain")
    full_payload["jurisdiction"] = enriched_summary.get("jurisdiction")
    full_payload["audit_type"] = enriched_summary.get("audit_type")

    return full_payload
