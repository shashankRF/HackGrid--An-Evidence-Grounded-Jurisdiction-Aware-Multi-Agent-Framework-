from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    SourceType,
    RequirementType,
    ApplicabilityStatus,
    MappingRelationship,
    GapStatus,
    GapAction,
    ExtractedRequirement,
    PolicyStandardMappingRecord,
    GenuineGapRecord,
    TechnicalImplication,
    RegulatoryImplication,
    HypothesisEvaluation,
    HypothesisStatus,
    DecisionSpecificSufficiency,
    CounterEvidenceItem,
    EvidenceRole,
)
from .requirement_extractor import extract_requirement_from_evidence


class PolicyStandardMappingEngine:
    """
    Core Policy ↔ Standard Mapping Engine for HackGrid.
    Enforces strict requirement-level comparison between international technical
    standards/recommendations (e.g. ITU-T Y.3172, 3GPP) and national provisions (e.g. Indian DoT/TEC/Acts).
    """

    def __init__(self, target_jurisdiction: str = "India"):
        self.target_jurisdiction = target_jurisdiction

    def map_evidence(
        self,
        evidence_records: List[Dict[str, Any]],
        question: str = "",
    ) -> Dict[str, Any]:
        """
        Execute deterministic policy/standard mapping over retrieved evidence.
        """
        # 1. Extract requirements from all records
        requirements: List[ExtractedRequirement] = []
        for i, rec in enumerate(evidence_records, start=1):
            req = extract_requirement_from_evidence(rec, i)
            requirements.append(req)

        # 2. Separate into International and National
        international_reqs: List[ExtractedRequirement] = []
        national_reqs: List[ExtractedRequirement] = []
        supporting_tech: List[ExtractedRequirement] = []

        for req in requirements:
            if req.jurisdiction == "International" or req.source_type in {
                SourceType.INTERNATIONAL_RECOMMENDATION,
                SourceType.INTERNATIONAL_TECHNICAL_STANDARD,
            }:
                if "y.3172" in req.document.lower() or "3gpp" in req.document.lower() or "etsi" in req.document.lower():
                    international_reqs.append(req)
                else:
                    supporting_tech.append(req)
            elif req.jurisdiction == self.target_jurisdiction or req.source_type in {
                SourceType.NATIONAL_REGULATION,
                SourceType.NATIONAL_POLICY,
                SourceType.NATIONAL_TECHNICAL_STANDARD,
                SourceType.LAW,
                SourceType.RULE,
            }:
                national_reqs.append(req)
            else:
                supporting_tech.append(req)

        # 3. Detect counter-evidence in the set
        counter_evidence_items: List[CounterEvidenceItem] = []
        for req in requirements:
            lower = req.requirement_text.lower()
            if any(term in lower for term in ["does not apply", "exemption", "exception", "not required", "advisory only", "voluntary", "independent of"]):
                counter_evidence_items.append(
                    CounterEvidenceItem(
                        evidence_id=req.evidence_id,
                        role=EvidenceRole.LIMITING,
                        relationship="Limits mandatory enforcement or operational scope",
                        explanation=f"Text in {req.document} indicates an exception or non-binding scope.",
                    )
                )

        # 4. Build Mappings
        mappings: List[PolicyStandardMappingRecord] = []
        gaps: List[GenuineGapRecord] = []

        # If international requirements exist, compare against national requirements
        if international_reqs:
            for idx, intl in enumerate(international_reqs, start=1):
                mapping_id = f"MAP-{idx:03d}"
                best_match: Optional[ExtractedRequirement] = None
                relationship = MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED
                reason = ""
                missing_elem = None

                # Look for corresponding national requirement
                if national_reqs:
                    for nat in national_reqs:
                        nat_text = nat.requirement_text.lower()
                        intl_text = intl.requirement_text.lower()

                        # 1. Additional sovereign requirement check (e.g. Lawful interception, data localization)
                        additional_terms = ["lawful interception", "data localization", "mandatory interception", "national security clearance"]
                        if any(term in nat_text for term in additional_terms) and not any(term in intl_text for term in additional_terms):
                            relationship = MappingRelationship.ADDITIONAL_NATIONAL_REQUIREMENT
                            best_match = nat
                            reason = (
                                f"National provision ({nat.document}) imposes an additional sovereign "
                                f"security requirement beyond the international technical framework ({intl.document})."
                            )
                            break

                        # 2. Substantive coverage check via semantic root overlap
                        stems_intl = set(w[:5] for w in intl_text.split() if len(w) >= 5)
                        stems_nat = set(w[:5] for w in nat_text.split() if len(w) >= 5)
                        common_stems = stems_intl.intersection(stems_nat)

                        has_domain_overlap = (
                            len(common_stems) >= 2
                            or ("slice" in intl_text and ("slice" in nat_text or "partition" in nat_text or "virtual" in nat_text))
                            or ("architectur" in intl_text and "architectur" in nat_text)
                            or ("network" in intl_text and "network" in nat_text and ("secur" in nat_text or "protect" in nat_text or "control" in nat_text))
                        )

                        if has_domain_overlap:
                            best_match = nat
                            # Does national cover all aspects?
                            is_partial = (
                                ("pipeline" in intl_text and "pipeline" not in nat_text)
                                or any(term in nat_text for term in ["omit", "omits", "does not cover", "lacks", "excluding", "partial"])
                            )
                            if is_partial:
                                relationship = MappingRelationship.PARTIALLY_COVERED
                                reason = (
                                    f"National provision ({nat.document}) addresses telecom network architecture and security aspects, "
                                    f"but does not specifically establish controls for the ML pipeline/sandbox architecture defined in {intl.document}."
                                )
                                missing_elem = "Dedicated ML pipeline and sandbox architectural controls."
                            else:
                                relationship = MappingRelationship.COVERED
                                reason = (
                                    f"National provision ({nat.document}) substantively addresses the technical/architectural controls "
                                    f"specified in {intl.document} despite phrasing differences."
                                )
                            break

                    if not best_match:
                        # National provisions exist in evidence, but none match this specific technical requirement
                        relationship = MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED
                        reason = (
                            f"Retrieved {self.target_jurisdiction} evidence does not establish substantive coverage for "
                            f"{intl.document} architectural requirement ({intl.requirement_summary[:80]}). "
                            "Absence of retrieved evidence does not prove regulatory absence."
                        )
                        missing_elem = f"Specific coverage for {intl.technology_domain} in retrieved national rules."
                else:
                    # No national provisions retrieved
                    relationship = MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED
                    reason = (
                        f"No applicable provision establishing {self.target_jurisdiction} coverage was identified in the supplied evidence set. "
                        "Absence protocol applies: non-retrieval does not establish statutory non-existence."
                    )
                    missing_elem = "No national evidence retrieved in active candidate pool."

                # Create mapping record
                national_payload = best_match.to_dict() if best_match else {
                    "requirement_id": "NAT-NONE",
                    "source": f"No applicable {self.target_jurisdiction} provision identified in supplied evidence",
                    "source_type": SourceType.OTHER.value,
                    "document": "NONE_RETRIEVED",
                    "clause": None,
                    "section": None,
                    "page": None,
                    "requirement_text": "No corresponding provision in retrieved evidence.",
                    "requirement_summary": "Not established in supplied KB evidence.",
                    "technology_domain": intl.technology_domain,
                    "jurisdiction": self.target_jurisdiction,
                    "status": RequirementType.UNKNOWN.value,
                    "applicability": ApplicabilityStatus.NOT_ESTABLISHED.value,
                    "evidence_id": "NONE",
                }

                counter_for_mapping = [item.to_dict() for item in counter_evidence_items]

                mapping_rec = PolicyStandardMappingRecord(
                    mapping_id=mapping_id,
                    international_requirement=intl.to_dict(),
                    national_provision=national_payload,
                    applicability="DIRECT" if best_match else "NOT_ESTABLISHED",
                    relationship=relationship,
                    reason=reason,
                    missing_element=missing_elem,
                    counter_evidence=counter_for_mapping,
                    evidence_confidence=0.90 if best_match else 0.50,
                    mapping_confidence=0.85 if best_match else 0.40,
                )
                mappings.append(mapping_rec)

                # Genuine Gap Test
                if relationship == MappingRelationship.PARTIALLY_COVERED:
                    gaps.append(
                        GenuineGapRecord(
                            gap_id=f"GAP-{idx:03d}",
                            international_requirement=intl.requirement_summary,
                            source=intl.document,
                            international_evidence_ids=[intl.evidence_id],
                            national_provision=best_match.requirement_summary if best_match else "Unknown",
                            national_evidence_ids=[best_match.evidence_id] if best_match else [],
                            applicability=intl.applicability.value,
                            coverage="Partially Covered",
                            status=GapStatus.ESTABLISHED_GAP if missing_elem else GapStatus.POTENTIAL_GAP_NOT_ESTABLISHED,
                            why=reason,
                            missing_element=missing_elem or "Specific architectural control not explicitly covered in national provision",
                            counter_evidence="Counter-evidence confirms high-level security duties apply.",
                            impact="Technical oversight ambiguity in ML pipeline deployments.",
                            action=GapAction.VERIFY,
                            required_action_detail="Verify whether upcoming DoT/TEC guidelines address ML pipeline controls.",
                        )
                    )
                elif relationship == MappingRelationship.POTENTIAL_GAP_NOT_ESTABLISHED:
                    gaps.append(
                        GenuineGapRecord(
                            gap_id=f"GAP-{idx:03d}",
                            international_requirement=intl.requirement_summary,
                            source=intl.document,
                            international_evidence_ids=[intl.evidence_id],
                            national_provision="Not established by retrieved evidence",
                            national_evidence_ids=[],
                            applicability=intl.applicability.value,
                            coverage="Potential Gap — Not Established",
                            status=GapStatus.POTENTIAL_GAP_NOT_ESTABLISHED,
                            why=reason,
                            missing_element="Substantive national provision unretrieved in current evidence set",
                            counter_evidence=(
                                "No meaningful counter-evidence was identified in the supplied Knowledge Base evidence set."
                                if not counter_evidence_items else "General telecom security provisions exist in framework."
                            ),
                            impact="Potential compliance uncertainty if technology is deployed without verified national guidance.",
                            action=GapAction.VERIFY,
                            required_action_detail=f"Verify applicable {self.target_jurisdiction} gazette notifications and TEC GR standards.",
                        )
                    )
                elif relationship == MappingRelationship.ADDITIONAL_NATIONAL_REQUIREMENT:
                    # Note: Additional National Requirement is NOT a gap!
                    pass

        # 5. Technical Implications (Evidence-grounded)
        technical_implications: List[TechnicalImplication] = []
        for i, req in enumerate(international_reqs[:3] + supporting_tech[:2], start=1):
            if "y.3172" in req.document.lower():
                technical_implications.append(
                    TechnicalImplication(
                        implication_id=f"TI-{i:03d}",
                        implication="ML pipeline functions in future telecom networks require sandboxing and overlay/underlay decoupling.",
                        evidence_ids=[req.evidence_id],
                        basis=f"Grounded in ITU-T Y.3172 architectural framework specification in {req.evidence_id}.",
                        status="ESTABLISHED",
                        limitation="Evidence defines architectural recommendation; specific vendor deployment configuration is not established.",
                    )
                )
            elif "slice" in req.requirement_text.lower() or "5g" in req.requirement_text.lower():
                technical_implications.append(
                    TechnicalImplication(
                        implication_id=f"TI-{i:03d}",
                        implication="Network slice instance selection and isolation require verified authentication and policy enforcement.",
                        evidence_ids=[req.evidence_id],
                        basis=f"Grounded in 3GPP/ETSI specifications retrieved in {req.evidence_id}.",
                        status="ESTABLISHED",
                        limitation="Evidence establishes technical specification; production slice telemetry is not established in KB.",
                    )
                )

        if not technical_implications and requirements:
            technical_implications.append(
                TechnicalImplication(
                    implication_id="TI-001",
                    implication="Technical requirement established by retrieved specification evidence.",
                    evidence_ids=[requirements[0].evidence_id],
                    basis=f"Retrieved from {requirements[0].document}.",
                    status="SUPPORTED",
                    limitation="Specific implementation details depend on operational deployment context.",
                )
            )

        # 6. Regulatory Implications (Strict 9-part guardrail)
        regulatory_implications: List[RegulatoryImplication] = []
        for i, req in enumerate(national_reqs[:3], start=1):
            if req.source_type in {SourceType.NATIONAL_REGULATION, SourceType.LAW}:
                regulatory_implications.append(
                    RegulatoryImplication(
                        implication_id=f"RI-{i:03d}",
                        implication=f"Operators in {req.jurisdiction} must comply with statutory requirements under {req.document}.",
                        evidence_ids=[req.evidence_id],
                        source_type=req.source_type.value,
                        jurisdiction=req.jurisdiction,
                        applicability="DIRECT",
                        status="ESTABLISHED",
                        basis=f"Retrieved statutory text from {req.document} in {req.evidence_id}.",
                        limitation="Specific incident reporting trigger threshold must be verified against factual evidence.",
                    )
                )

        # If no national regulation retrieved
        if not regulatory_implications:
            regulatory_implications.append(
                RegulatoryImplication(
                    implication_id="RI-001",
                    implication=f"Mandatory regulatory obligation is NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE.",
                    evidence_ids=[req.evidence_id for req in requirements[:2]],
                    source_type="NONE_ESTABLISHED",
                    jurisdiction=self.target_jurisdiction,
                    applicability="NOT_ESTABLISHED",
                    status="NOT_ESTABLISHED",
                    basis="The supplied Knowledge Base evidence set does not establish an applicable mandatory statutory trigger.",
                    limitation="Absence of retrieved regulatory trigger does not prove absence of all telecom law.",
                )
            )

        # 7. Decision-Specific Evidence Sufficiency
        has_intl = len(international_reqs) > 0
        has_nat = len(national_reqs) > 0

        sufficiency = DecisionSpecificSufficiency(
            overall_evidence="SUFFICIENT" if (has_intl or has_nat) else "INSUFFICIENT",
            requirement_mapping="SUFFICIENT" if (has_intl and has_nat) else "INSUFFICIENT_EVIDENCE",
            risk_assessment="SUFFICIENT FOR PRELIMINARY RISK SCREENING",
            regulatory_conclusion="ESTABLISHED" if has_nat else "NOT ESTABLISHED BY THE SUPPLIED KNOWLEDGE BASE EVIDENCE",
            root_cause="NOT ESTABLISHED" if ("incident" in question.lower()) else "NOT APPLICABLE",
        )

        return {
            "extracted_requirements": [req.to_dict() for req in requirements],
            "international_requirements": [req.to_dict() for req in international_reqs],
            "national_provisions": [req.to_dict() for req in national_reqs],
            "mappings": [m.to_dict() for m in mappings],
            "gaps": [g.to_dict() for g in gaps],
            "technical_implications": [ti.to_dict() for ti in technical_implications],
            "regulatory_implications": [ri.to_dict() for ri in regulatory_implications],
            "counter_evidence": [ce.to_dict() for ce in counter_evidence_items],
            "sufficiency": sufficiency.to_dict(),
        }
