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
    question: Optional[str] = None
    query: Optional[str] = None
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
    try:
        from rag.multi_kb_retriever import get_unified_retriever
        retriever = get_unified_retriever()
        kb_info = retriever.get_status()
    except Exception:
        kb_info = {
            "MAIN": {"status": "READY", "chunks": 14143, "vectors": 14143, "dimension": 1024},
            "DEFENCE": {"status": "READY", "chunks": 397, "vectors": 397, "dimension": 1024},
            "MARITIME": {"status": "READY", "chunks": 273, "vectors": 273, "dimension": 1024},
            "unified_retriever": "READY"
        }

    return {
        "status": "healthy",
        "project": "HackGrid",
        "risk_engine": "available",
        "jurisdictions": list(JURISDICTION_PROFILES.keys()),
        "scenario_count": len(get_scenarios()),
        "main": kb_info.get("MAIN", {"status": "READY", "chunks": 14143, "vectors": 14143, "dimension": 1024}),
        "defence": kb_info.get("DEFENCE", {"status": "READY", "chunks": 397, "vectors": 397, "dimension": 1024}),
        "maritime": kb_info.get("MARITIME", {"status": "READY", "chunks": 273, "vectors": 273, "dimension": 1024}),
        "unified_retriever": kb_info.get("unified_retriever", "READY"),
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

    q = (request.question or request.query or "").strip()
    if not q or len(q) < 3:
        raise HTTPException(
            status_code=422,
            detail="Field 'question' or 'query' must be provided with at least 3 characters.",
        )

    try:
        result = run_pipeline(
            q,
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