from pydantic import BaseModel
from typing import Any, Optional


class WorkflowRequest(BaseModel):
    instruction: str
    file_path: Optional[str] = None


class ExecutionStep(BaseModel):
    step_number: int
    tool_name: str
    input: dict[str, Any]
    output: str
    duration_ms: float
    timestamp: str
    reasoning: Optional[str] = None
    status: str = "completed"


class WorkflowResponse(BaseModel):
    instruction: str
    status: str
    result: str
    execution_log: list[ExecutionStep]
    total_duration_ms: float


class UploadResponse(BaseModel):
    file_path: str
    filename: str
    size_bytes: int
