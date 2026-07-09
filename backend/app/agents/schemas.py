from datetime import datetime

from pydantic import BaseModel, Field


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
    output: dict | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float | None = None
    task_id: str | None = None


class OrchestratorRun(BaseModel):
    run_id: str
    user_id: str
    goal: str
    status: str = AgentStatus.PENDING
    tasks: list[AgentTask] = Field(default_factory=list)
    results: dict[str, AgentResult] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str | None = None
    error: str | None = None
