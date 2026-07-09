from datetime import datetime

from pydantic import BaseModel, Field


class TaskDef(BaseModel):
    agent: str
    action: str
    params: dict = Field(default_factory=dict)
    priority: int = 5


class OrchestratorResult(BaseModel):
    run_id: str
    user_id: str
    goal: str
    status: str = "pending"
    tasks: list[TaskDef] = Field(default_factory=list)
    results: dict = Field(default_factory=dict)
    error: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str | None = None


class OrchestratorRequest(BaseModel):
    goal: str


class OrchestratorStatus(BaseModel):
    run_id: str
    status: str
    results: dict = Field(default_factory=dict)
    error: str | None = None
