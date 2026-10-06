from .models import Scenario, ScenarioStep


SCENARIOS = [

    # ============================================================
    # DEFENCE
    # ============================================================

    Scenario(
        scenario_id="HG-DEFENCE-001",
        title="UAV Tactical Datalink Interference",
        domain="Defence",
        jurisdiction="India",
        description=(
            "Simulated defence scenario involving a UAV experiencing "
            "unexpected tactical datalink degradation and suspected "
            "interference or spoofing."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="D1",
                title="Initial anomaly",
                event=(
                    "A tactical UAV begins experiencing intermittent "
                    "loss of command-and-control link quality."
                ),
                evidence_prompt=(
                    "What technical standards, security requirements, "
                    "or documented mechanisms are relevant to UAV "
                    "communications interference and link security?"
                ),
            ),
            ScenarioStep(
                step_id="D2",
                title="Suspected interference",
                event=(
                    "Signal measurements suggest abnormal interference "
                    "rather than an ordinary communications failure."
                ),
                evidence_prompt=(
                    "What evidence is required to distinguish ordinary "
                    "communication degradation from deliberate interference "
                    "or spoofing?"
                ),
            ),
            ScenarioStep(
                step_id="D3",
                title="Operational assessment",
                event=(
                    "The operator must determine whether the incident "
                    "requires escalation to a human defence authority."
                ),
                evidence_prompt=(
                    "What evidence, limitations, and governance considerations "
                    "should influence the final assessment?"
                ),
            ),
        ],
    ),

    # ============================================================
    # MARITIME
    # ============================================================

    Scenario(
        scenario_id="HG-MARITIME-002",
        title="AIS and GNSS Vessel Behaviour Anomaly",
        domain="Maritime",
        jurisdiction="India",
        description=(
            "Simulated maritime incident in which AIS behaviour and "
            "navigation information become inconsistent."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="M1",
                title="AIS anomaly detected",
                event=(
                    "A vessel's AIS track shows an abrupt and unusual "
                    "change in reported position and course."
                ),
                evidence_prompt=(
                    "What standards, technical requirements, and known "
                    "mechanisms are relevant to AIS integrity and maritime "
                    "navigation anomalies?"
                ),
            ),
            ScenarioStep(
                step_id="M2",
                title="Navigation inconsistency",
                event=(
                    "AIS information becomes inconsistent with other "
                    "available navigation observations."
                ),
                evidence_prompt=(
                    "What evidence should be examined before concluding "
                    "that a vessel navigation anomaly represents spoofing, "
                    "manipulation, equipment failure, or another cause?"
                ),
            ),
            ScenarioStep(
                step_id="M3",
                title="Maritime risk assessment",
                event=(
                    "The operator must determine the confidence of the "
                    "assessment and whether escalation is required."
                ),
                evidence_prompt=(
                    "What evidence gaps and uncertainty should be reported "
                    "before making a consequential maritime assessment?"
                ),
            ),
        ],
    ),

    # ============================================================
    # TELECOM / 5G
    # ============================================================

    Scenario(
        scenario_id="HG-5G-003",
        title="5G Network Slice Security Incident",
        domain="Telecom/5G",
        jurisdiction="India",
        description=(
            "Simulated 5G incident involving suspected compromise or "
            "isolation failure affecting a network slice."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="T1",
                title="Slice anomaly",
                event=(
                    "A network slice begins showing unexpected traffic "
                    "behaviour and isolation anomalies."
                ),
                evidence_prompt=(
                    "What 3GPP and Indian requirements apply to security "
                    "and isolation of 5G network slices?"
                ),
            ),
            ScenarioStep(
                step_id="T2",
                title="Security investigation",
                event=(
                    "The operator suspects that traffic from one slice "
                    "may have affected another logical service boundary."
                ),
                evidence_prompt=(
                    "Which technical security controls and requirements "
                    "are relevant to preventing or detecting cross-slice "
                    "security problems?"
                ),
            ),
            ScenarioStep(
                step_id="T3",
                title="Compliance assessment",
                event=(
                    "The operator needs to determine whether the observed "
                    "condition represents a technical or regulatory gap."
                ),
                evidence_prompt=(
                    "Compare applicable technical and Indian regulatory "
                    "requirements and identify evidence-supported gaps."
                ),
            ),
        ],
    ),

    # ============================================================
    # TELECOM RANSOMWARE
    # ============================================================

    Scenario(
        scenario_id="HG-TELECOM-004",
        title="Telecom OSS/BSS Ransomware Incident",
        domain="Telecom/5G",
        jurisdiction="India",
        description=(
            "Simulated ransomware incident affecting telecom operational "
            "and business support systems."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="R1",
                title="Service disruption",
                event=(
                    "Multiple operator management systems become unavailable "
                    "following a suspected ransomware event."
                ),
                evidence_prompt=(
                    "What cybersecurity requirements and controls are "
                    "relevant to protecting critical telecom systems?"
                ),
            ),
            ScenarioStep(
                step_id="R2",
                title="Root-cause investigation",
                event=(
                    "Investigators identify several possible initial-access "
                    "paths but lack sufficient evidence to select one."
                ),
                evidence_prompt=(
                    "What evidence is required to establish or reject "
                    "possible root causes of a telecom cyber incident?"
                ),
            ),
            ScenarioStep(
                step_id="R3",
                title="Recovery decision",
                event=(
                    "Management must decide whether available evidence "
                    "supports operational recovery."
                ),
                evidence_prompt=(
                    "What evidence limitations and human-review requirements "
                    "should be considered before making a consequential decision?"
                ),
            ),
        ],
    ),

    # ============================================================
    # RESEARCH
    # ============================================================

    Scenario(
        scenario_id="HG-RESEARCH-005",
        title="Conflicting O-RAN Security Research",
        domain="Research",
        jurisdiction="European Union",
        description=(
            "Simulated research-analysis scenario involving conflicting "
            "technical findings concerning O-RAN security and network "
            "efficiency."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="RS1",
                title="Research question",
                event=(
                    "A research team wants to determine whether an O-RAN "
                    "security mechanism introduces measurable performance "
                    "or energy overhead."
                ),
                evidence_prompt=(
                    "What published standards and technical evidence "
                    "address the relevant O-RAN security mechanisms?"
                ),
            ),
            ScenarioStep(
                step_id="RS2",
                title="Conflicting findings",
                event=(
                    "Two groups report apparently different conclusions "
                    "about security overhead."
                ),
                evidence_prompt=(
                    "Identify supporting, contradicting, contextual, and "
                    "insufficient evidence relevant to the research question."
                ),
            ),
            ScenarioStep(
                step_id="RS3",
                title="Research gap",
                event=(
                    "The research team wants to determine whether a genuine "
                    "research gap remains."
                ),
                evidence_prompt=(
                    "Does the available evidence establish a research gap, "
                    "or is the evidence insufficient to establish one?"
                ),
            ),
        ],
    ),

    # ============================================================
    # EUROPEAN UNION
    # ============================================================

    Scenario(
        scenario_id="HG-EU-006",
        title="European 5G Network Function Security Incident",
        domain="Telecom/5G",
        jurisdiction="European Union",
        description=(
            "Simulated European 5G incident involving a suspected security "
            "weakness in a network function and a need to assess applicable "
            "European requirements."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="EU1",
                title="Network-function anomaly",
                event=(
                    "A 5G network function reports abnormal authentication "
                    "and access behaviour."
                ),
                evidence_prompt=(
                    "What technical standards and European requirements "
                    "are relevant to securing the affected 5G network function?"
                ),
            ),
            ScenarioStep(
                step_id="EU2",
                title="Regulatory applicability",
                event=(
                    "The operator must determine which European regulatory "
                    "requirements may apply."
                ),
                evidence_prompt=(
                    "Identify applicable European regulatory requirements "
                    "from the available evidence and distinguish mandatory "
                    "requirements from technical standards or guidance."
                ),
            ),
            ScenarioStep(
                step_id="EU3",
                title="Compliance assessment",
                event=(
                    "The operator needs an evidence-supported assessment "
                    "of coverage and potential gaps."
                ),
                evidence_prompt=(
                    "Compare the applicable European requirements with the "
                    "technical evidence and identify established gaps or "
                    "insufficient evidence."
                ),
            ),
        ],
    ),

    # ============================================================
    # ENTERPRISE INCIDENT
    # ============================================================

    Scenario(
        scenario_id="HG-ENTERPRISE-007",
        title="Conflicting Evidence Cyber Incident",
        domain="Enterprise Incident",
        jurisdiction="India",
        description=(
            "Simulated enterprise cyber incident where several indicators "
            "suggest compromise but the available evidence is incomplete "
            "and partially conflicting."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="E1",
                title="Initial alert",
                event=(
                    "Security monitoring detects unusual authentication "
                    "activity across multiple systems."
                ),
                evidence_prompt=(
                    "What documented security controls or requirements "
                    "are relevant to the observed behaviour?"
                ),
            ),
            ScenarioStep(
                step_id="E2",
                title="Conflicting indicators",
                event=(
                    "Some indicators support compromise while others "
                    "suggest a legitimate administrative operation."
                ),
                evidence_prompt=(
                    "Identify supporting and contradicting evidence and "
                    "determine whether compromise is actually established."
                ),
            ),
            ScenarioStep(
                step_id="E3",
                title="Human decision",
                event=(
                    "A security analyst must determine whether the evidence "
                    "is sufficient for escalation."
                ),
                evidence_prompt=(
                    "Assess evidence quality, uncertainty, and whether "
                    "human review is required before escalation."
                ),
            ),
        ],
    ),
]


def get_scenarios():
    return [scenario.to_dict() for scenario in SCENARIOS]


def get_scenario(scenario_id: str):
    for scenario in SCENARIOS:
        if scenario.scenario_id == scenario_id:
            return scenario.to_dict()

    return None