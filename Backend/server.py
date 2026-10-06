from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .risk_engine_api import router as risk_router
from .audit_api import router as audit_router
from .orchestrator import run_pipeline
from .demo_scenarios import get_scenarios, get_scenario
from rag.retrieval import JURISDICTION_PROFILES


app = FastAPI(
    title="HackGrid Backend",
    version="1.0",
    description="HackGrid Evidence Intelligence Backend",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5501", "http://127.0.0.1:5501", "http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Existing Risk Engine
# ============================================================

app.include_router(risk_router)
app.include_router(audit_router)


# ============================================================
# Request Models
# ============================================================

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    jurisdiction: str = "India"


class ScenarioRunRequest(BaseModel):
    scenario_id: str
    jurisdiction: str = "India"
    step_id: Optional[str] = None


# ============================================================
# Helpers
# ============================================================

def validate_jurisdiction(jurisdiction: str):
    if jurisdiction not in JURISDICTION_PROFILES:
        supported = ", ".join(JURISDICTION_PROFILES.keys())

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported jurisdiction profile '{jurisdiction}'. "
                f"Supported jurisdiction profiles: {supported}"
            ),
        )


# ============================================================
# Basic Endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "project": "HackGrid",
        "backend": "FastAPI",
        "version": "1.0",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "project": "HackGrid",
        "risk_engine": "available",
        "jurisdictions": list(JURISDICTION_PROFILES.keys()),
        "scenario_count": len(get_scenarios()),
    }


# ============================================================
# Jurisdiction Endpoint
# ============================================================

@app.get("/api/jurisdictions")
def jurisdictions():
    return {
        "jurisdictions": [
            {
                "name": name,
                "included_sources": sorted(list(sources)),
            }
            for name, sources in JURISDICTION_PROFILES.items()
        ]
    }


# ============================================================
# Query Endpoint
# ============================================================

@app.post("/api/query")
def query(request: QueryRequest):
    validate_jurisdiction(request.jurisdiction)

    try:
        result = run_pipeline(
            request.question,
            jurisdiction=request.jurisdiction,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {exc}",
        )


# ============================================================
# Scenario Endpoints
# ============================================================

@app.get("/api/scenarios")
def scenarios():
    return {
        "scenarios": get_scenarios()
    }


@app.get("/api/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str):
    scenario = get_scenario(scenario_id)

    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_id}' not found.",
        )

    return scenario


@app.post("/api/scenarios/run")
def run_scenario(request: ScenarioRunRequest):
    validate_jurisdiction(request.jurisdiction)

    scenario = get_scenario(request.scenario_id)

    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{request.scenario_id}' not found.",
        )

    steps = scenario.get("steps", [])

    if not steps:
        raise HTTPException(
            status_code=400,
            detail="Scenario contains no execution steps.",
        )

    selected_step = None

    if request.step_id:
        for step in steps:
            if step["step_id"] == request.step_id:
                selected_step = step
                break

        if selected_step is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Step '{request.step_id}' not found "
                    f"in scenario '{request.scenario_id}'."
                ),
            )
    else:
        selected_step = steps[0]

    question = selected_step["evidence_prompt"]

    try:
        pipeline_result = run_pipeline(
            question,
            jurisdiction=request.jurisdiction,
        )

        return {
            "scenario": {
                "scenario_id": scenario["scenario_id"],
                "title": scenario["title"],
                "domain": scenario["domain"],
                "simulated": scenario["simulated"],
                "default_jurisdiction": scenario["jurisdiction"],
                "selected_jurisdiction": request.jurisdiction,
            },
            "scenario_step": selected_step,
            "pipeline_result": pipeline_result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Scenario execution failed: {exc}",
        )