import logging
import io
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.hiring_agent.service import HiringAgentService
from app.hiring_agent.schemas import (
    PipelineResult, ATSScore, JDMatchResult, ExtractedResume,
)

logger = logging.getLogger("agentforge.api.hiring_agent")
router = APIRouter()


class CoverLetterRequest(BaseModel):
    jd_text: str
    company_name: str | None = None
    candidate_name: str | None = None
    tone: str = "professional"
    length: str = "medium"


class JDMatchRequest(BaseModel):
    jd_text: str
    github_url: str | None = None
    portfolio_url: str | None = None


class ATSRequest(BaseModel):
    jd_text: str


class EvaluateTextRequest(BaseModel):
    resume_text: str
    position_type: str | None = None
    jd_text: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


@router.post("/pipeline", response_model=PipelineResult)
async def run_full_pipeline(
    file: UploadFile = File(...),
    jd_text: str = Form(None),
    position_type: str = Form(None),
    github_url: str = Form(None),
    portfolio_url: str = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="File too large (max 10MB)")
    service = HiringAgentService(db, str(user.id))
    result = await service.run_pipeline(
        pdf_content=content, jd_text=jd_text, position_type=position_type,
        github_url=github_url, portfolio_url=portfolio_url,
    )
    if not result:
        raise HTTPException(500, detail="Pipeline failed to extract resume data")
    return result


@router.post("/extract", response_model=ExtractedResume)
async def extract_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="File too large (max 10MB)")
    service = HiringAgentService(db, str(user.id))
    resume = await service.extract_resume(content)
    return resume


@router.post("/evaluate-text")
async def evaluate_text(
    data: EvaluateTextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = HiringAgentService(db, str(user.id))
    github_text = ""
    portfolio_text = ""
    if data.github_url:
        gh = await service.enrich_github(data.github_url)
        if gh.get("profile"):
            repos = gh.get("repositories", [])
            top = sorted([r for r in repos if not r.get("is_fork")], key=lambda r: r.get("stars", 0), reverse=True)[:5]
            github_text = f"\nGitHub: {gh['profile'].get('name','')} - {gh['profile'].get('followers',0)} followers"
            if top:
                github_text += "\nTop repos:\n" + "\n".join(f"- {r['name']} (⭐{r['stars']})" for r in top)
    if data.portfolio_url:
        pf = await service.enrich_portfolio(data.portfolio_url)
        if pf.get("title"):
            portfolio_text = f"\nPortfolio: {pf['title']}"
            if pf.get("technologies_detected"):
                portfolio_text += f"\nTechnologies: {', '.join(pf['technologies_detected'][:10])}"
    eval_text = data.resume_text
    if github_text:
        eval_text += "\n" + github_text
    if portfolio_text:
        eval_text += "\n" + portfolio_text
    evaluation = await service.evaluate_resume(eval_text, data.position_type)
    if not evaluation:
        raise HTTPException(500, detail="Evaluation failed")
    improvements = await service.generate_improvements(evaluation)
    return {"evaluation": evaluation.model_dump(), "improvements": [i.model_dump() for i in improvements]}


@router.post("/ats", response_model=ATSScore)
async def ats_analysis(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="File too large (max 10MB)")
    service = HiringAgentService(db, str(user.id))
    resume = await service.extract_resume(content)
    if not resume or not resume.raw_text:
        raise HTTPException(500, detail="Failed to extract resume text")
    return await service.compute_ats_analysis(resume.raw_text, jd_text)


@router.post("/match-jd")
async def match_jd(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
    github_url: str = Form(None),
    portfolio_url: str = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="File too large (max 10MB)")
    service = HiringAgentService(db, str(user.id))
    resume = await service.extract_resume(content)
    if not resume or not resume.raw_text:
        raise HTTPException(500, detail="Failed to extract resume text")
    gh_text = ""
    pf_text = ""
    if github_url:
        gh = await service.enrich_github(github_url)
        if gh.get("profile"):
            repos = gh.get("repositories", [])
            top = sorted([r for r in repos if not r.get("is_fork")], key=lambda r: r.get("stars", 0), reverse=True)[:5]
            gh_text = f"\nGitHub: {gh['profile'].get('name','')} - {gh['profile'].get('followers',0)} followers"
            if top:
                gh_text += "\n" + "\n".join(f"- {r['name']}" for r in top)
    if portfolio_url:
        pf = await service.enrich_portfolio(portfolio_url)
        if pf.get("title"):
            pf_text = f"\nPortfolio: {pf['title']}"
    result = await service.match_jd(resume.raw_text, jd_text, gh_text, pf_text)
    if not result:
        raise HTTPException(500, detail="JD matching failed")
    return result.model_dump()


@router.post("/cover-letter")
async def generate_cover_letter(
    file: UploadFile = File(...),
    data: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import json
    try:
        params = json.loads(data)
        req = CoverLetterRequest(**params)
    except Exception as e:
        raise HTTPException(400, detail=f"Invalid JSON body: {e}")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="File too large (max 10MB)")
    service = HiringAgentService(db, str(user.id))
    resume = await service.extract_resume(content)
    if not resume or not resume.raw_text:
        raise HTTPException(500, detail="Failed to extract resume text")
    name = resume.basics.name if resume.basics else None
    letter = await service.generate_cover_letter(
        resume.raw_text, req.jd_text, name, req.company_name, req.tone, req.length,
    )
    if not letter:
        raise HTTPException(500, detail="Cover letter generation failed")
    return {"cover_letter": letter, "candidate_name": name or "Candidate", "company": req.company_name}


@router.get("/github-enrich")
async def github_enrich(
    url: str = Query(..., description="GitHub profile URL"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = HiringAgentService(db, str(user.id))
    return await service.enrich_github(url)


@router.get("/portfolio-enrich")
async def portfolio_enrich(
    url: str = Query(..., description="Portfolio website URL"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = HiringAgentService(db, str(user.id))
    return await service.enrich_portfolio(url)


@router.post("/live-demos")
async def check_live_demos(
    urls: list[str],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not urls:
        raise HTTPException(400, detail="URL list is empty")
    if len(urls) > 50:
        raise HTTPException(400, detail="Too many URLs (max 50)")
    service = HiringAgentService(db, str(user.id))
    return await service.check_live_demos(urls)


@router.get("/history")
async def get_history(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = HiringAgentService(db, str(user.id))
    return {"items": await service.get_history(limit)}


@router.post("/report")
async def generate_report(
    file: UploadFile = File(...),
    position_type: str = Form(None),
    github_url: str = Form(None),
    portfolio_url: str = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="File too large (max 10MB)")
    service = HiringAgentService(db, str(user.id))
    result = await service.run_pipeline(
        pdf_content=content, position_type=position_type,
        github_url=github_url, portfolio_url=portfolio_url,
    )
    if not result:
        raise HTTPException(500, detail="Pipeline failed")
    html = await service.generate_report_html(result)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html, media_type="text/html")
