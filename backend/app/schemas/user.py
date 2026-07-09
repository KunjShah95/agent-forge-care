from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr

# ─── Users ──────────────────────────────────────────────────


class UserOut(BaseModel):
    id: UUID
    email: str
    email_verified: bool = False
    full_name: str
    avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


# ─── Skills ─────────────────────────────────────────────────


class AddSkillRequest(BaseModel):
    name: str
    proficiency: str = "intermediate"


class SkillOut(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ProfileSkillOut(BaseModel):
    skill: SkillOut
    proficiency: str

    model_config = {"from_attributes": True}


# ─── Profiles ───────────────────────────────────────────────


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    school: str | None = None
    graduation_date: date | None = None
    bio: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    target_locations: list[str] | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    role_types: list[str] | None = None
    company_sizes: list[str] | None = None
    career_goal: str | None = None
    is_onboarded: bool | None = None
    skills: list[AddSkillRequest] | None = None


class ProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str | None = None
    avatar_url: str | None = None
    school: str | None = None
    graduation_date: date | None = None
    bio: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    target_locations: list[str] = []
    salary_min: int | None = None
    salary_max: int | None = None
    role_types: list[str] = []
    company_sizes: list[str] = []
    career_goal: str | None = None
    is_onboarded: bool = False
    skills: list[ProfileSkillOut] = []

    model_config = {"from_attributes": True}


# ─── Opportunities ──────────────────────────────────────────


class OpportunityOut(BaseModel):
    id: UUID
    title: str
    company: str
    company_logo: str | None = None
    location: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    industry: str | None = None
    remote: bool = False
    work_type: str | None = None
    type: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "USD"
    posted_date: date | None = None
    deadline: date | None = None
    description: str | None = None
    apply_url: str | None = None
    company_size: str | None = None
    skills_required: list[str] = []
    source: str | None = None
    match_score: float | None = None
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
    opportunity_id: UUID
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    stage: str | None = None
    notes: str | None = None
    next_step: str | None = None
    next_date: date | None = None


class ApplicationOut(BaseModel):
    id: UUID
    opportunity_id: UUID
    stage: str
    applied_date: date | None = None
    next_step: str | None = None
    next_date: date | None = None
    notes: str | None = None
    resume_version: str | None = None
    cover_letter: str | None = None
    created_at: datetime
    updated_at: datetime
    opportunity: OpportunityOut | None = None

    model_config = {"from_attributes": True}


class ApplicationList(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int


# ─── Contacts ───────────────────────────────────────────────


class ContactCreate(BaseModel):
    name: str
    role: str | None = None
    company: str | None = None
    email: EmailStr | None = None
    linkedin_url: str | None = None
    phone: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    company: str | None = None
    email: EmailStr | None = None
    linkedin_url: str | None = None
    phone: str | None = None
    status: str | None = None
    last_contact: date | None = None
    notes: str | None = None


class ContactOut(BaseModel):
    id: UUID
    name: str
    role: str | None = None
    company: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    phone: str | None = None
    status: str
    last_contact: date | None = None
    notes: str | None = None
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
    id: UUID
    agent_type: str
    status: str
    input: dict | None = None
    output: dict | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskList(BaseModel):
    items: list[TaskOut]


class PlannerRunResponse(BaseModel):
    task_id: UUID


# ─── Memory ─────────────────────────────────────────────────


class MemoryCreate(BaseModel):
    key: str
    value: Any
    weight: float = 1.0


class MemoryUpdate(BaseModel):
    value: Any | None = None
    weight: float | None = None


class MemoryOut(BaseModel):
    id: UUID
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
    email_notify: bool = False


class AlertConfigUpdate(BaseModel):
    name: str | None = None
    keywords: list[str] | None = None
    locations: list[str] | None = None
    opportunity_types: list[str] | None = None
    min_match_score: int | None = None
    frequency: str | None = None
    is_active: bool | None = None
    email_notify: bool | None = None


class AlertConfigOut(BaseModel):
    id: UUID
    name: str
    keywords: list[str] = []
    locations: list[str] = []
    opportunity_types: list[str] = []
    min_match_score: int = 80
    frequency: str = "daily"
    is_active: bool = True
    email_notify: bool = False
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
    focus: str = "company"
    topics: list[str] = []


class InternshipDiscoverRequest(BaseModel):
    query: str = "internship"
    location: str | None = None
    skills: list[str] = []


class JobDiscoverRequest(BaseModel):
    query: str = "software engineer"
    location: str | None = None
    skills: list[str] = []


class CoverLetterRequest(BaseModel):
    company: str
    role: str
    application_id: str | None = None


class ResumeTailorRequest(BaseModel):
    role_type: str = "internship"
    target_company: str | None = None
    skills: list[str] = []


class MonitorSettingsUpdate(BaseModel):
    keywords: list[str] | None = None
    locations: list[str] | None = None
    opportunity_types: list[str] | None = None
    min_match_score: int | None = None
    max_results: int | None = None
    frequency: str | None = None
    digest: bool | None = None
    push: bool | None = None
    realtime: bool | None = None


class EnrichRequest(BaseModel):
    github_url: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None


class EnrichResult(BaseModel):
    github_profile: dict = {}
    github_analysis: dict = {}
    portfolio_data: dict = {}
    social_links: dict = {}
    discovered_skills: list[str] = []
    status: str = "completed"
    message: str = ""


class CareerGuidanceRequest(BaseModel):
    query: str
    context: dict | None = None


class NetworkingOutreachRequest(BaseModel):
    target_companies: list[str]
    role: str | None = None
    skills: list[str] | None = None


# ─── Notifications ──────────────────────────────────────────


class NotificationOut(BaseModel):
    id: UUID
    title: str
    body: str
    type: str
    read: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationOut]


# ─── Resume ──────────────────────────────────────────────


class ResumeOut(BaseModel):
    filename: str
    pages: int
    characters: int
    uploaded_at: str | None = None


class ResumeList(BaseModel):
    items: list[ResumeOut]
    total: int


# ─── Interview Sessions ──────────────────────────────────


class InterviewSessionOut(BaseModel):
    id: str
    company: str
    type: str
    date: str
    score: int | None = None
    duration: str | None = None


class InterviewSessionList(BaseModel):
    items: list[InterviewSessionOut]


class InterviewSessionCreate(BaseModel):
    company: str
    type: str
    score: int | None = None
    duration: str | None = None


# ─── Interview Feedback ──────────────────────────────────


class InterviewFeedbackRequest(BaseModel):
    question: str
    answer: str
    company: str | None = None
    role: str | None = None


# ─── DeveloperProfile Composite ─────────────────────────────


class RepoSummary(BaseModel):
    name: str
    full_name: str
    description: str | None = None
    language: str | None = None
    stars: int = 0
    forks: int = 0
    topics: list[str] = []
    html_url: str = ""
    homepage: str | None = None
    updated_at: str | None = None


class CommitFrequency(BaseModel):
    by_day: dict[str, int] = {}
    by_hour: dict[str, int] = {}
    by_day_of_week: dict[str, int] = {}


class CommitHistory(BaseModel):
    total_commits: int = 0
    total_unique_commits: int = 0
    commits_by_repo: dict[str, list[str]] = {}
    commit_languages: dict[str, int] = {}
    commit_frequency: CommitFrequency = CommitFrequency()
    average_commits_per_day: float = 0.0
    recent_events: list[dict] = []


class ContributionCalendar(BaseModel):
    total_contributions: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    top_contribution_months: list[dict] = []
    contribution_calendar: list[dict] = []


class OSSContributions(BaseModel):
    total_prs: int = 0
    total_issues: int = 0
    pull_requests: list[dict] = []
    repos_contributed_to: list[str] = []
    summary: str = ""


class CommitAnalysis(BaseModel):
    coding_frequency: str = "unknown"
    preferred_work_days: list[str] = []
    commit_quality: str = "unknown"
    project_focus: str = "unknown"
    oss_participation: str = "unknown"
    consistency_score: int = 0
    experience_indicators: list[str] = []
    summary: str = ""


class SkillAnalysis(BaseModel):
    skills: list[str] = []
    primary_languages: list[str] = []
    project_highlights: list[str] = []
    experience_level: str = "unknown"
    interests: list[str] = []
    professional_summary: str = ""


class DeveloperProfile(BaseModel):
    """Complete composite developer profile — merges all GitHub data sources."""
    username: str
    profile_url: str
    avatar_url: str | None = None
    name: str | None = None
    bio: str | None = None
    location: str | None = None
    company: str | None = None
    email: str | None = None
    twitter_handle: str | None = None
    blog_url: str | None = None
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    total_stars: int = 0
    languages: dict[str, int] = {}
    repositories: list[RepoSummary] = []
    skills: SkillAnalysis = SkillAnalysis()
    commit_history: CommitHistory | None = None
    contributions: ContributionCalendar | None = None
    oss_contributions: OSSContributions | None = None
    commit_analysis: CommitAnalysis | None = None
    data_completeness: int = 0  # 0-100: how many data sources loaded
    errors: list[str] = []

