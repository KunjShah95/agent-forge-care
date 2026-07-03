from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


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
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


class OrchestratorRequest(BaseModel):
    goal: str


class OrchestratorStatus(BaseModel):
    run_id: str
    status: str
    results: dict = Field(default_factory=dict)
    error: Optional[str] = None
