import os
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.agent.core import WorkflowAgent
from app.models.schemas import UploadResponse, WorkflowRequest, WorkflowResponse

router = APIRouter()


@router.post("/run", response_model=WorkflowResponse, summary="Run a workflow")
async def run_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """
    Accept a natural-language instruction and an optional file_path.
    The agent decides which tools to call, in what order, and returns
    the result plus a full execution log.

    Example body:
    ```json
    {
      "instruction": "Analyze the sales data and generate a summary report",
      "file_path": "uploads/sales.csv"
    }
    ```
    """
    t0 = time.time()
    agent = WorkflowAgent()

    try:
        result, execution_log = agent.run(
            instruction=request.instruction,
            file_path=request.file_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return WorkflowResponse(
        instruction=request.instruction,
        status="success",
        result=result,
        execution_log=execution_log,
        total_duration_ms=round((time.time() - t0) * 1_000, 2),
    )


@router.post("/upload", response_model=UploadResponse, summary="Upload a file")
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a CSV or text file.  Returns the server-side file_path to pass
    into subsequent /run requests.
    """
    upload_dir = Path(os.environ.get("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / file.filename
    content = await file.read()
    dest.write_bytes(content)

    return UploadResponse(
        file_path=str(dest),
        filename=file.filename,
        size_bytes=len(content),
    )


@router.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "AI Workflow Automation Agent"}
