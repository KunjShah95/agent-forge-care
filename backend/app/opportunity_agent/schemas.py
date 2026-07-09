from pydantic import BaseModel, Field


class ScoredOpportunityItem(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    description: str = ""
    skills_required: list[str] = []
    match_score: float = 0.0
    reason: str = ""
    industry: str | None = None
    work_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    apply_url: str | None = None
    company_size: str | None = None
    source: str | None = None
    posted_date: str | None = None


class OpportunityFeedback(BaseModel):
    overall_assessment: str = Field(..., description="2-3 sentence assessment of the opportunity set")
    top_matches_summary: str = Field(..., description="Summary of the best matches found")
    skill_gaps: list[str] = Field(default_factory=list, description="Skills the user is missing for these roles")
    improvement_suggestions: list[str] = Field(
        default_factory=list, description="Actionable suggestions to improve match quality"
    )
    search_refinements: list[str] = Field(
        default_factory=list, description="Ways to refine the search for better results"
    )
    market_insight: str | None = Field(None, description="Brief market insight about demand for these roles")


class OpportunityAnalysis(BaseModel):
    total_found: int
    high_match_count: int
    average_score: float
    top_industries: list[str] = Field(default_factory=list)
    common_skills: list[str] = Field(default_factory=list)
    remote_ratio: float = 0.0


class OpportunityResult(BaseModel):
    items: list[ScoredOpportunityItem]
    total: int
    agent: str
    message: str
    summary: str
    analysis: OpportunityAnalysis
    feedback: OpportunityFeedback
    search_metadata: dict = Field(default_factory=dict)


class OpportunityScanResult(BaseModel):
    items: list[ScoredOpportunityItem]
    total: int
    scored: int
    alerts: list[dict] = Field(default_factory=list)
    message: str
    analysis: OpportunityAnalysis | None = None
    feedback: OpportunityFeedback | None = None
