from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AgentStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTask(BaseModel):
    agent_type: str
    action: str
    params: dict = Field(default_factory=dict)
    priority: int = 5


class AgentResult(BaseModel):
    agent_type: str
    status: str = AgentStatus.PENDING
    output: Optional[dict] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    task_id: Optional[str] = None


class OrchestratorRun(BaseModel):
    run_id: str
    user_id: str
    goal: str
    status: str = AgentStatus.PENDING
    tasks: list[AgentTask] = Field(default_factory=list)
    results: dict[str, AgentResult] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
