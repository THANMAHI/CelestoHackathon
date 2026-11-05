import re
import os
from typing import Literal, Dict, Any, List
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.ledger.db import db

app = FastAPI(title="Celesto Run Ledger API", version="1.0.0")

SANDBOX_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")
VALID_STATES = {"created", "ready", "running", "succeeded", "failed", "deleted"}
VALID_EXECUTION_TARGET = "celesto_sandbox"

class RunCreateRequest(BaseModel):
    run_id: str = Field(..., description="Unique run identifier")
    sandbox_name: str = Field(..., description="Sandbox name matching sbx-[a-z0-9]{8,}")
    problem_id: str = Field(..., description="Identifier of the task or problem")
    state: str = Field(..., description="Lifecycle state of the run")
    execution_target: str = Field(..., description="Target execution environment, must be celesto_sandbox")

@app.get("/health", status_code=status.HTTP_200_OK)
def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/api/runs", status_code=status.HTTP_200_OK)
def list_runs() -> List[Dict[str, Any]]:
    runs = db.get_runs()
    return runs

@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(run: RunCreateRequest):
    # Validate execution target
    if run.execution_target != VALID_EXECUTION_TARGET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid execution_target: '{run.execution_target}'. Must be '{VALID_EXECUTION_TARGET}'."
        )

    # Validate state
    if run.state not in VALID_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state: '{run.state}'. Allowed states: {sorted(list(VALID_STATES))}."
        )

    # Validate sandbox name format
    if not SANDBOX_REGEX.match(run.sandbox_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sandbox_name: '{run.sandbox_name}'. Must match 'sbx-' followed by 8 or more lowercase alphanumeric characters."
        )

    # Store run
    stored = db.insert_run(run.model_dump())
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=stored)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8080))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=False)
