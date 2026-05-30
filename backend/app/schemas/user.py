from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ───────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ─── Users ──────────────────────────────────────────────────


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


# ─── Skills ─────────────────────────────────────────────────


class SkillOut(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class ProfileSkillOut(BaseModel):
    skill: SkillOut
    proficiency: str

    model_config = {"from_attributes": True}


# ─── Profiles ───────────────────────────────────────────────


class ProfileUpdate(BaseModel):
    school: Optional[str] = None
    graduation_date: Optional[date] = None
    bio: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    target_locations: Optional[list[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    role_types: Optional[list[str]] = None
    company_sizes: Optional[list[str]] = None
    career_goal: Optional[str] = None
    is_onboarded: Optional[bool] = None


class ProfileOut(BaseModel):
    id: str
    user_id: str
    school: Optional[str] = None
    graduation_date: Optional[date] = None
    bio: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    target_locations: list[str] = []
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    role_types: list[str] = []
    company_sizes: list[str] = []
    career_goal: Optional[str] = None
    is_onboarded: bool = False
    skills: list[ProfileSkillOut] = []

    model_config = {"from_attributes": True}


class AddSkillRequest(BaseModel):
    name: str
    proficiency: str = "intermediate"


# ─── Opportunities ──────────────────────────────────────────


class OpportunityOut(BaseModel):
    id: str
    title: str
    company: str
    company_logo: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    type: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    posted_date: Optional[date] = None
    deadline: Optional[date] = None
    description: Optional[str] = None
    apply_url: Optional[str] = None
    company_size: Optional[str] = None
    skills_required: list[str] = []
    source: Optional[str] = None
    match_score: Optional[float] = None
    match_reasons: list[str] = []

    model_config = {"from_attributes": True}


class OpportunityList(BaseModel):
    items: list[OpportunityOut]
    total: int
    page: int


class ScoredOpportunityOut(OpportunityOut):
    match_score: float
    match_reasons: list[str]


class ScoredOpportunityList(BaseModel):
    items: list[ScoredOpportunityOut]


# ─── Applications ───────────────────────────────────────────


class ApplicationCreate(BaseModel):
    opportunity_id: str
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    stage: Optional[str] = None
    notes: Optional[str] = None
    next_step: Optional[str] = None
    next_date: Optional[date] = None


class ApplicationOut(BaseModel):
    id: str
    opportunity_id: str
    stage: str
    applied_date: Optional[date] = None
    next_step: Optional[str] = None
    next_date: Optional[date] = None
    notes: Optional[str] = None
    resume_version: Optional[str] = None
    cover_letter: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    opportunity: Optional[OpportunityOut] = None

    model_config = {"from_attributes": True}


class ApplicationList(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int


# ─── Contacts ───────────────────────────────────────────────


class ContactCreate(BaseModel):
    name: str
    role: Optional[str] = None
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    last_contact: Optional[date] = None
    notes: Optional[str] = None


class ContactOut(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    status: str
    last_contact: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactList(BaseModel):
    items: list[ContactOut]
    total: int
    page: int


# ─── Agents ─────────────────────────────────────────────────


class PlannerRunRequest(BaseModel):
    goal: str


class TaskOut(BaseModel):
    id: str
    agent_type: str
    status: str
    input: Optional[dict] = None
    output: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskList(BaseModel):
    items: list[TaskOut]


class PlannerRunResponse(BaseModel):
    task_id: str


# ─── Memory ─────────────────────────────────────────────────


class MemoryCreate(BaseModel):
    key: str
    value: Any
    weight: float = 1.0


class MemoryUpdate(BaseModel):
    value: Optional[Any] = None
    weight: Optional[float] = None


class MemoryOut(BaseModel):
    id: str
    key: str
    value: Any
    weight: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryList(BaseModel):
    items: list[MemoryOut]
    total: int
    page: int


# ─── Analytics ──────────────────────────────────────────────


class AnalyticsSummary(BaseModel):
    active_matches: int = 0
    applications: int = 0
    interview_rate: float = 0
    deadlines: int = 0


class FunnelPoint(BaseModel):
    name: str
    value: int
    rate: str


class SkillDemand(BaseModel):
    skill: str
    demand: float


class ActivityPoint(BaseModel):
    day: str
    applications: int
    interviews: int


# ─── Monitor ────────────────────────────────────────────────


class AlertConfigCreate(BaseModel):
    name: str
    keywords: list[str] = []
    locations: list[str] = []
    opportunity_types: list[str] = []
    min_match_score: int = 80
    frequency: str = "daily"
    is_active: bool = True


class AlertConfigUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[list[str]] = None
    locations: Optional[list[str]] = None
    opportunity_types: Optional[list[str]] = None
    min_match_score: Optional[int] = None
    frequency: Optional[str] = None
    is_active: Optional[bool] = None


class AlertConfigOut(BaseModel):
    id: str
    name: str
    keywords: list[str] = []
    locations: list[str] = []
    opportunity_types: list[str] = []
    min_match_score: int = 80
    frequency: str = "daily"
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertConfigList(BaseModel):
    items: list[AlertConfigOut]
    total: int
    page: int


class InterviewPrepRequest(BaseModel):
    company: str
    role: str
    type: str = "behavioral"


class ResearchRequest(BaseModel):
    company: str


class CoverLetterRequest(BaseModel):
    company: str
    role: str
    application_id: Optional[str] = None


class ResumeTailorRequest(BaseModel):
    role_type: str = "internship"
    target_company: Optional[str] = None
    skills: list[str] = []


class MonitorSettingsUpdate(BaseModel):
    keywords: Optional[list[str]] = None
    locations: Optional[list[str]] = None
    opportunity_types: Optional[list[str]] = None
    min_match_score: Optional[int] = None
    max_results: Optional[int] = None
    frequency: Optional[str] = None
