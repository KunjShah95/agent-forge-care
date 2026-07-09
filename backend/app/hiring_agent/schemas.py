from pydantic import BaseModel, Field


class CategoryScore(BaseModel):
    score: float = Field(ge=0, description="Score achieved")
    max: int = Field(gt=0, description="Maximum possible score")
    evidence: str = Field(..., min_length=1, description="Supporting evidence")


class Scores(BaseModel):
    open_source: CategoryScore
    self_projects: CategoryScore
    production: CategoryScore
    technical_skills: CategoryScore


class BonusPoints(BaseModel):
    total: float = Field(ge=0, le=20, description="Total bonus points")
    breakdown: str = Field(..., description="Breakdown of bonus points")


class Deductions(BaseModel):
    total: float = Field(ge=0, description="Total deductions")
    reasons: str = Field(..., description="Reasons for deductions")


class EvaluationData(BaseModel):
    scores: Scores
    bonus_points: BonusPoints
    deductions: Deductions
    key_strengths: list[str] = Field(..., min_length=1, max_length=5)
    areas_for_improvement: list[str] = Field(..., min_length=1, max_length=5)


class ResumeBasics(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    url: str | None = None
    summary: str | None = None
    location: str | None = None
    profiles: list[dict] | None = None


class ResumeWork(BaseModel):
    model_config = {"populate_by_name": True}
    name: str | None = None
    position: str | None = None
    url: str | None = None
    start_date: str | None = Field(None, alias="startDate")
    end_date: str | None = Field(None, alias="endDate")
    summary: str | None = None
    highlights: list[str] | None = None


class ResumeEducation(BaseModel):
    model_config = {"populate_by_name": True}
    institution: str | None = None
    area: str | None = None
    study_type: str | None = Field(None, alias="studyType")
    start_date: str | None = Field(None, alias="startDate")
    end_date: str | None = Field(None, alias="endDate")
    score: str | None = None


class ResumeSkill(BaseModel):
    name: str | None = None
    level: str | None = None
    keywords: list[str] | None = None


class ResumeProject(BaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None
    technologies: list[str] | None = None
    highlights: list[str] | None = None


class ResumeAward(BaseModel):
    title: str | None = None
    date: str | None = None
    awarder: str | None = None
    summary: str | None = None


class ExtractedResume(BaseModel):
    basics: ResumeBasics | None = None
    work: list[ResumeWork] | None = None
    education: list[ResumeEducation] | None = None
    skills: list[ResumeSkill] | None = None
    projects: list[ResumeProject] | None = None
    awards: list[ResumeAward] | None = None
    raw_text: str | None = None


class ATSScore(BaseModel):
    keyword_coverage_pct: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    matched_count: int
    missing_count: int
    suggestions: list[str]
    experience_years: int | None = None
    resume_experience_years: int | None = None


class JDMatchResult(BaseModel):
    skill_match: dict
    experience_match: dict
    education_match: dict
    project_relevance: dict
    overall_score: int
    overall_assessment: str
    gap_analysis: list[dict]


class ImprovementItem(BaseModel):
    category: str
    suggestion: str
    impact: str = "medium"
    effort: str = "medium"
    priority_score: int = 5


class PipelineResult(BaseModel):
    name: str
    resume: ExtractedResume
    overall_score: float
    max_score: int
    evaluation: EvaluationData
    improvements: list[ImprovementItem]
    live_demo_status: list[dict]
    github_summary: dict | None = None
    portfolio_summary: dict | None = None
    report_html: str | None = None
