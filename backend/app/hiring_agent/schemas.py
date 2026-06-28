from typing import Optional
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
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    profiles: Optional[list[dict]] = None


class ResumeWork(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[list[str]] = None


class ResumeEducation(BaseModel):
    institution: Optional[str] = None
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None


class ResumeSkill(BaseModel):
    name: Optional[str] = None
    level: Optional[str] = None
    keywords: Optional[list[str]] = None


class ResumeProject(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    technologies: Optional[list[str]] = None
    highlights: Optional[list[str]] = None


class ResumeAward(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class ExtractedResume(BaseModel):
    basics: Optional[ResumeBasics] = None
    work: Optional[list[ResumeWork]] = None
    education: Optional[list[ResumeEducation]] = None
    skills: Optional[list[ResumeSkill]] = None
    projects: Optional[list[ResumeProject]] = None
    awards: Optional[list[ResumeAward]] = None
    raw_text: Optional[str] = None


class ATSScore(BaseModel):
    keyword_coverage_pct: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    matched_count: int
    missing_count: int
    suggestions: list[str]
    experience_years: Optional[int] = None
    resume_experience_years: Optional[int] = None


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
    github_summary: Optional[dict] = None
    portfolio_summary: Optional[dict] = None
    report_html: Optional[str] = None
