import io
import logging
from datetime import datetime

import pypdf
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.memory.memory_layer import AgentMemory
from app.models.user import AgentTask, AgentType, MemoryEntry, Profile, ProfileSkill, TaskStatus, User
from app.schemas.user import ResumeList, ResumeOut
from app.services.memory_service import MemoryService
from app.utils.embedding import get_text_embedding

logger = logging.getLogger("agentforge.resume")

TECH_KEYWORDS = [
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "golang",
    "rust",
    "c++",
    "c#",
    "ruby",
    "swift",
    "kotlin",
    "scala",
    "php",
    "perl",
    "r",
    "matlab",
    "sql",
    "bash",
    "shell",
    "react",
    "angular",
    "vue",
    "next.js",
    "node.js",
    "express",
    "django",
    "flask",
    "spring",
    "fastapi",
    "graphql",
    "rest",
    "api",
    "docker",
    "kubernetes",
    "k8s",
    "aws",
    "azure",
    "gcp",
    "terraform",
    "ansible",
    "jenkins",
    "ci/cd",
    "git",
    "linux",
    "nginx",
    "redis",
    "mongodb",
    "postgresql",
    "mysql",
    "elasticsearch",
    "kafka",
    "rabbitmq",
    "grpc",
    "websocket",
    "machine learning",
    "deep learning",
    "ai",
    "llm",
    "nlp",
    "computer vision",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "langchain",
    "rag",
    "vector database",
    "openai",
    "hugging face",
    "llama",
    "gpt",
    "bert",
    "transformer",
    "agent",
    "autogen",
    "crewai",
    "tailwind",
    "sass",
    "redux",
    "webpack",
    "vite",
    "jest",
    "cypress",
    "pandas",
    "numpy",
    "jupyter",
    "spark",
    "hadoop",
    "airflow",
    "dbt",
    "microservices",
    "serverless",
    "lambda",
    "containers",
    "orchestration",
    "oauth",
    "jwt",
    "saml",
    "ldap",
    "ssl",
    "tls",
    "https",
    "agile",
    "scrum",
    "kanban",
    "jira",
    "confluence",
    "tableau",
    "power bi",
    "looker",
    "datadog",
    "grafana",
    "prometheus",
]

ACTION_VERBS = [
    "achieved",
    "analyzed",
    "built",
    "conducted",
    "created",
    "delivered",
    "designed",
    "developed",
    "established",
    "evaluated",
    "executed",
    "expanded",
    "generated",
    "identified",
    "implemented",
    "improved",
    "increased",
    "initiated",
    "integrated",
    "introduced",
    "launched",
    "led",
    "managed",
    "negotiated",
    "optimized",
    "organized",
    "performed",
    "planned",
    "produced",
    "reduced",
    "reorganized",
    "resolved",
    "revamped",
    "streamlined",
    "strengthened",
    "structured",
    "supervised",
    "transformed",
    "upgraded",
    "accelerated",
    "automated",
    "consolidated",
    "coordinated",
    "cultivated",
    "demonstrated",
    "deployed",
    "engineered",
    "facilitated",
    "formulated",
    "oversaw",
]

SECTION_HEADERS = [
    "experience",
    "education",
    "skills",
    "projects",
    "work experience",
    "employment",
    "summary",
    "objective",
    "certifications",
    "publications",
    "leadership",
]

router = APIRouter()


@router.get("", response_model=ResumeList)
async def list_resumes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key.like("resume_%"),
            )
            .order_by(MemoryEntry.created_at.desc())
        )
        entries = result.scalars().all()
        items = []
        for e in entries:
            val = e.value or {}
            items.append(
                ResumeOut(
                    filename=val.get("filename", e.key.replace("resume_", "")),
                    pages=val.get("pages", 0),
                    characters=val.get("characters", 0),
                    uploaded_at=e.created_at.isoformat() if e.created_at else None,
                )
            )
        return ResumeList(items=items, total=len(items))
    except Exception as e:
        logger.error("Failed to list resumes for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list resumes: {str(e)}")


@router.get("/ats-analysis")
async def ats_analysis(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze the most recently uploaded resume for ATS keyword/format/verb gaps."""
    try:
        result = await db.execute(
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key.like("resume_%"),
            )
            .order_by(MemoryEntry.created_at.desc())
            .limit(1)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="No resume found. Upload a resume first.")

        resume_text = (entry.value or {}).get("text", "")
        if not resume_text:
            raise HTTPException(status_code=404, detail="Resume text is empty.")

        text_lower = resume_text.lower()
        total_words = max(len(resume_text.split()), 1)

        profile_result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.skills).selectinload(ProfileSkill.skill))
            .where(Profile.user_id == user.id)
        )
        profile = profile_result.scalar_one_or_none()

        skill_names = []
        if profile and profile.skills:
            for ps in profile.skills:
                skill_names.append(ps.skill.name)

        present_keywords = []
        missing_keywords = []
        for name in skill_names:
            if name.lower() in text_lower:
                present_keywords.append(name)
            else:
                missing_keywords.append(name)

        keyword_score = 0
        if skill_names:
            keyword_score = round((len(present_keywords) / len(skill_names)) * 100)

        tech_present = []
        tech_missing = []
        for kw in TECH_KEYWORDS:
            if kw.lower() in text_lower:
                tech_present.append(kw)
            else:
                tech_missing.append(kw)
        tech_coverage = round((len(tech_present) / len(TECH_KEYWORDS)) * 100) if TECH_KEYWORDS else 0

        # ── Fetch GitHub skills analysis from memory ──
        github_analysis = None
        github_raw = None
        try:
            mem_service = MemoryService(db)
            github_analysis = await mem_service.get_memory(str(user.id), "github_skills_analysis")
            github_raw = await mem_service.get_memory(str(user.id), "github_profile_raw")
        except Exception as e:
            logger.debug("GitHub memory unavailable for ATS analysis: %s", e)

        github_suggestions = []
        github_inferred_skills = []
        github_demonstrated_skills = []
        project_evidence = []

        if github_analysis and isinstance(github_analysis, dict) and "error" not in github_analysis:
            # Extract skills inferred from GitHub
            gh_skills = github_analysis.get("skills", [])
            gh_langs = github_analysis.get("primary_languages", [])
            gh_projects = github_analysis.get("project_highlights", [])
            gh_exp_level = github_analysis.get("experience_level", "")

            # Categorize GitHub skills
            for skill in gh_skills:
                skill_lower = skill.lower()
                in_profile = any(s.lower() == skill_lower for s in skill_names)
                in_resume = skill_lower in text_lower

                if not in_resume and in_profile:
                    # Skill is in profile + GitHub but missing from resume — high priority
                    github_demonstrated_skills.append(skill)
                    github_suggestions.append(
                        f"Your GitHub shows proven expertise in {skill} — add it to your resume with a project example"
                    )
                elif not in_resume and not in_profile:
                    # Skill is inferred from GitHub but not in profile or resume
                    github_inferred_skills.append(skill)
                    github_suggestions.append(
                        f"GitHub activity suggests {skill} proficiency — consider adding it to your profile skills and resume"
                    )

            # Build project evidence from top repos
            if gh_projects:
                for project in gh_projects[:3]:
                    project_evidence.append(str(project))

            # Mention experience level in GitHub-specific suggestions
            if gh_exp_level and gh_exp_level != "junior":
                github_suggestions.append(
                    f"GitHub analysis suggests {gh_exp_level}-level expertise — ensure your resume reflects this seniority with impact metrics"
                )

            # Add language-specific suggestions
            if gh_langs:
                missing_langs = [lang for lang in gh_langs if lang.lower() not in text_lower]
                if missing_langs:
                    github_suggestions.append(
                        f"Highlight your GitHub-proven skills in {', '.join(missing_langs[:3])} on your resume"
                    )

        # Also show raw repo stats
        github_repo_count = 0
        github_stars = 0
        if github_raw and isinstance(github_raw, dict) and "profile" in github_raw:
            github_repo_count = github_raw.get("profile", {}).get("public_repos", 0)
            github_stars = github_raw.get("total_stars", 0)

        # ── Fetch portfolio scrape data from memory ──
        portfolio_data = None
        try:
            portfolio_data = await mem_service.get_memory(str(user.id), "portfolio_scrape")
        except Exception as e:
            logger.debug("Portfolio memory unavailable for ATS analysis: %s", e)

        portfolio_suggestions = []
        portfolio_inferred_skills = []
        portfolio_projects = []
        portfolio_experience = []
        portfolio_role = None

        if portfolio_data and isinstance(portfolio_data, dict) and "error" not in portfolio_data:
            pf_skills = portfolio_data.get("skills", [])
            pf_technologies = portfolio_data.get("technologies_detected", [])
            pf_projects = portfolio_data.get("projects", [])
            pf_experience = portfolio_data.get("experience", [])
            portfolio_data.get("summary", "")
            portfolio_role = portfolio_data.get("role")

            # Combine all portfolio-detected skills
            all_pf_skills = list(set((pf_skills or []) + (pf_technologies or [])))

            for skill in all_pf_skills:
                skill_lower = skill.lower()
                in_profile = any(s.lower() == skill_lower for s in skill_names)
                in_resume = skill_lower in text_lower

                if not in_resume and in_profile:
                    portfolio_suggestions.append(
                        f"Your portfolio website shows {skill} proficiency — add it to your resume with project context"
                    )
                    portfolio_inferred_skills.append(skill)
                elif not in_resume and not in_profile:
                    portfolio_suggestions.append(
                        f"Portfolio mentions {skill} — consider adding it to your profile and resume"
                    )
                    portfolio_inferred_skills.append(skill)

            # Add project-specific suggestions
            if pf_projects:
                for project in pf_projects[:3]:
                    portfolio_projects.append(str(project))
                portfolio_suggestions.append(
                    f"Include portfolio projects like {', '.join(str(p) for p in pf_projects[:3])} on your resume"
                )

            # Add experience-specific suggestions
            if pf_experience:
                for exp in pf_experience[:2]:
                    portfolio_experience.append(str(exp))
                portfolio_suggestions.append(
                    "Your portfolio lists work experience not reflected in your resume — consider adding relevant entries"
                )

            # Role-specific suggestion
            if portfolio_role:
                portfolio_suggestions.append(
                    f"Portfolio shows you as a {portfolio_role} — ensure your resume title aligns with this"
                )

        # Combine all GitHub-verified skills for scoring
        all_gh_skills = list(set(github_demonstrated_skills + github_inferred_skills))
        all_pf_skills = list(set(portfolio_inferred_skills))

        found_sections = [s for s in SECTION_HEADERS if s in text_lower]
        format_score = min(100, round(len(found_sections) / 7 * 100))

        verb_count = sum(1 for v in ACTION_VERBS if v in text_lower)
        verb_density = verb_count / 50
        action_verb_score = min(100, round(verb_density * 100))

        # Boost keyword score if GitHub shows skills not yet on resume
        if all_gh_skills:
            # Count how many GitHub-inferred skills appear in resume
            gh_in_resume = sum(1 for s in all_gh_skills if s.lower() in text_lower)
            gh_ratio = gh_in_resume / max(len(all_gh_skills), 1)
            # Boost: if user has skills on GitHub but hasn't listed them, they lose points
            if gh_ratio < 0.5:
                keyword_score = max(0, keyword_score - 10)

        suggestions = []
        if len(found_sections) < 4:
            missing_sections = [s for s in ["experience", "education", "skills", "projects"] if s not in found_sections]
            suggestions.append(f"Add missing sections: {', '.join(missing_sections)}")
        if verb_count < 8:
            suggestions.append("Use more action verbs to strengthen your bullet points")
        if total_words < 300:
            suggestions.append("Expand resume content for better ATS parsing")
        if "quantif" not in text_lower and "number" not in text_lower and "%" not in text_lower:
            suggestions.append("Add quantifiable results with numbers and percentages")
        if missing_keywords:
            suggestions.append(f"Add missing skills: {', '.join(missing_keywords[:5])}")
        if keyword_score < 50 and not missing_keywords:
            suggestions.append("Tailor your resume with more relevant keywords")

        # Add tech keyword suggestions
        if tech_coverage < 30:
            suggestions.append(
                f"Tech keyword score low ({tech_coverage}%). Add industry-standard technologies to improve ATS match"
            )
        elif 30 <= tech_coverage < 60:
            tech_high_value = [
                kw
                for kw in TECH_KEYWORDS
                if kw
                in ["kubernetes", "docker", "aws", "ci/cd", "terraform", "graphql", "react", "python", "typescript"]
                and kw.lower() not in text_lower
            ]
            if tech_high_value:
                suggestions.append(f"Missing high-demand keywords: {', '.join(tech_high_value[:4])}")

        # Append GitHub and portfolio-powered suggestions (they're more specific)
        suggestions.extend(github_suggestions[:4])
        suggestions.extend(portfolio_suggestions[:3])

        if not suggestions:
            suggestions.append("Resume looks well-optimized for ATS scanning")

        # Build enriched summary
        summary = (
            f"Your resume scores {keyword_score}/100 on keyword match, "
            f"{format_score}/100 on structure, and {action_verb_score}/100 on action verb usage."
        )

        # Add GitHub context to summary
        if github_repo_count > 0:
            summary += f" | GitHub: {github_repo_count} public repos, {github_stars} total stars"
        if github_demonstrated_skills:
            summary += f" | {len(github_demonstrated_skills)} GitHub-proven skills missing from resume"
        if project_evidence:
            summary += " | Add project evidence to strengthen your application"

        # Add portfolio context to summary
        if portfolio_role:
            summary += f" | Portfolio role: {portfolio_role}"
        if portfolio_projects:
            summary += f" | {len(portfolio_projects)} portfolio projects available"
        if portfolio_inferred_skills:
            summary += f" | {len(portfolio_inferred_skills)} portfolio skills not in resume"

        if keyword_score >= 80 and format_score >= 80 and action_verb_score >= 80:
            if not github_demonstrated_skills and not portfolio_inferred_skills:
                summary += " Overall, it is well-optimized for ATS systems."
            else:
                summary += (
                    " Resume structure is strong, but add your GitHub/portfolio-proven skills to maximize matches."
                )
        elif keyword_score < 50:
            summary += " Consider adding more relevant skills and keywords."
        if tech_coverage < 30:
            summary += " Tech keyword presence is low. Add modern technologies to improve discoverability."

        return {
            "format_score": format_score,
            "keyword_score": keyword_score,
            "action_verb_score": action_verb_score,
            "missing_keywords": missing_keywords,
            "present_keywords": present_keywords,
            "tech_keyword_coverage": tech_coverage,
            "tech_keywords_present": tech_present,
            "tech_keywords_missing_count": len(tech_missing),
            "github_inferred_skills": github_inferred_skills,
            "github_demonstrated_skills": github_demonstrated_skills,
            "project_evidence": project_evidence,
            "portfolio_skills": portfolio_inferred_skills,
            "portfolio_projects": portfolio_projects,
            "portfolio_role": portfolio_role,
            "suggestions": suggestions,
            "summary": summary,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to analyze ATS for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze ATS: {str(e)}")


@router.get("/search")
async def search_resume(
    q: str = Query(..., min_length=2),
    user: User = Depends(get_current_user),
):
    """Search resume chunks using Qdrant and return top matches."""
    # Input validation
    if not q or not isinstance(q, str) or len(q.strip()) < 2:
        raise HTTPException(
            status_code=422, detail="Search query must be a non-empty string with at least 2 characters"
        )

    try:
        vector = await get_text_embedding(q)
        agent_memory = AgentMemory(str(user.id))
        results = agent_memory.search_vectors("resume_embeddings", vector, limit=10)
        items = []
        for r in results:
            payload = r.payload if hasattr(r, "payload") else {}
            items.append(
                {
                    "text": payload.get("text", "")[:800],
                    "filename": payload.get("filename"),
                    "chunk_index": payload.get("chunk_index"),
                    "pages": payload.get("pages"),
                    "characters": payload.get("characters"),
                    "score": getattr(r, "score", None),
                }
            )
        return {"items": items}
    except Exception as e:
        logger.error("Failed to search resume for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to search resume: {str(e)}")


@router.delete("/{filename:path}", status_code=204)
async def delete_resume(
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not filename or not isinstance(filename, str) or len(filename.strip()) < 1:
        raise HTTPException(status_code=422, detail="Filename must be a non-empty string")

    try:
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key == f"resume_{filename}",
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="Resume not found")
        await db.delete(entry)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete resume for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete resume: {str(e)}")


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Input validation
    if not file.filename or not isinstance(file.filename, str):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        from app.hiring_agent.pdf_extractor import extract_pdf_text as _smart_extract

        text = _smart_extract(content)
    except Exception:
        logger.debug("Hiring agent PDF extractor unavailable, falling back to pypdf")
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            text = text.strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")

    text = text.strip()
    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        pages = len(pdf_reader.pages)
    except Exception:
        pages = 0
    chars = len(text)

    try:
        result = await db.execute(
            select(MemoryEntry).where(
                MemoryEntry.user_id == user.id,
                MemoryEntry.key == f"resume_{file.filename}",
            )
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.value = {
                "text": text,
                "filename": file.filename,
                "pages": pages,
                "characters": chars,
            }
        else:
            entry = MemoryEntry(
                user_id=user.id,
                key=f"resume_{file.filename}",
                value={
                    "text": text,
                    "filename": file.filename,
                    "pages": pages,
                    "characters": chars,
                },
            )
            db.add(entry)
        await db.flush()

        # --- Chunk resume text and index chunks in Qdrant (vector store) ---
        try:
            chunk_size = 1000
            chunk_overlap = 200
            agent_memory = AgentMemory(str(user.id))
            start = 0
            idx = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk = text[start:end]
                vector = await get_text_embedding(chunk)
                agent_memory.store_vector(
                    collection="resume_embeddings",
                    text=chunk,
                    vector=vector,
                    metadata={
                        "filename": file.filename,
                        "pages": pages,
                        "characters": chars,
                        "chunk_index": idx,
                    },
                )
                idx += 1
                start += chunk_size - chunk_overlap
        except Exception:
            # Do not fail the upload if embedding/indexing fails
            logger.exception("Failed to index resume chunks into Qdrant")

        # --- Enqueue background research tasks using RQ (reliable async processing) ---
        try:
            from redis import Redis
            from rq import Queue

            from app.tasks.agent_tasks import process_research_task

            redis = Redis.from_url(settings.redis_url)
            q = Queue("default", connection=redis)

            # fetch latest profile for URLs
            p = await db.execute(select(Profile).where(Profile.user_id == user.id))
            profile = p.scalar_one_or_none()

            if profile and profile.github_url:
                # create AgentTask record in DB (queued)
                task = AgentTask(
                    user_id=user.id,
                    agent_type=AgentType.research,
                    status=TaskStatus.queued,
                    input={"query": profile.github_url, "focus": "company"},
                )
                db.add(task)
                await db.commit()
                # enqueue background job with task id
                q.enqueue(process_research_task, str(task.id), str(user.id), profile.github_url, "company")

            if profile and profile.portfolio_url:
                task = AgentTask(
                    user_id=user.id,
                    agent_type=AgentType.research,
                    status=TaskStatus.queued,
                    input={"query": profile.portfolio_url, "focus": "company"},
                )
                db.add(task)
                await db.commit()
                q.enqueue(process_research_task, str(task.id), str(user.id), profile.portfolio_url, "company")
        except Exception:
            # best-effort; don't block upload
            logger.exception("Failed to enqueue background research tasks")

        return {
            "filename": file.filename,
            "pages": pages,
            "characters": chars,
            "text": text[:5000],
        }
    except Exception as e:
        logger.error("Failed to upload resume for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")


class ResumeSection(BaseModel):
    title: str
    content: list[str]


class ResumeData(BaseModel):
    name: str
    email: str
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    summary: str | None = None
    sections: list[ResumeSection]


class CoverLetterData(BaseModel):
    name: str
    email: str
    phone: str | None = None
    company: str
    date: str | None = None
    body: str


@router.post("/generate-pdf")
async def generate_resume_pdf(
    data: ResumeData,
    user: User = Depends(get_current_user),
):
    # Input validation
    if not data.name or not isinstance(data.name, str) or len(data.name.strip()) < 2:
        raise HTTPException(status_code=422, detail="Name must be a non-empty string with at least 2 characters")

    if not data.email or not isinstance(data.email, str) or "@" not in data.email:
        raise HTTPException(status_code=422, detail="Valid email is required")

    if not data.sections or not isinstance(data.sections, list) or len(data.sections) == 0:
        raise HTTPException(status_code=422, detail="At least one section is required")

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)

        styles = getSampleStyleSheet()

        name_style = ParagraphStyle(
            "ResumeName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_CENTER,
        )

        contact_style = ParagraphStyle(
            "ResumeContact",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
        )

        section_title_style = ParagraphStyle(
            "ResumeSectionTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1E3A8A"),
            alignment=TA_LEFT,
            spaceAfter=4,
        )

        body_style = ParagraphStyle(
            "ResumeBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            alignment=TA_LEFT,
        )

        bullet_style = ParagraphStyle(
            "ResumeBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#334155"),
            alignment=TA_LEFT,
            leftIndent=15,
            firstLineIndent=-10,
        )

        story = []

        # Header block
        story.append(Paragraph(data.name, name_style))
        story.append(Spacer(1, 4))

        contact_parts = []
        if data.email:
            contact_parts.append(data.email)
        if data.phone:
            contact_parts.append(data.phone)
        if data.linkedin:
            contact_parts.append(data.linkedin)
        if data.github:
            contact_parts.append(data.github)

        contact_str = "  |  ".join(contact_parts)
        story.append(Paragraph(contact_str, contact_style))
        story.append(Spacer(1, 15))

        # Summary Section
        if data.summary:
            story.append(Paragraph("PROFESSIONAL SUMMARY", section_title_style))
            story.append(Paragraph(data.summary, body_style))
            story.append(Spacer(1, 10))

        # Sections
        for sec in data.sections:
            sec_title = sec.title.upper()
            content_items = sec.content
            if not content_items:
                continue

            story.append(Paragraph(sec_title, section_title_style))

            if "SKILL" in sec_title:
                skills_str = ", ".join(content_items)
                story.append(Paragraph(skills_str, body_style))
            else:
                for item in content_items:
                    if item.startswith("-") or item.startswith("•"):
                        clean_item = item.lstrip("-•").strip()
                        story.append(Paragraph(f"&bull; {clean_item}", bullet_style))
                    else:
                        story.append(Paragraph(item, body_style))
            story.append(Spacer(1, 10))

        doc.build(story)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume_tailored.pdf"},
        )
    except Exception as e:
        logger.error("Failed to generate resume PDF for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/generate-cover-letter-pdf")
async def generate_cover_letter_pdf(
    data: CoverLetterData,
    user: User = Depends(get_current_user),
):
    # Input validation
    if not data.name or not isinstance(data.name, str) or len(data.name.strip()) < 2:
        raise HTTPException(status_code=422, detail="Name must be a non-empty string with at least 2 characters")

    if not data.email or not isinstance(data.email, str) or "@" not in data.email:
        raise HTTPException(status_code=422, detail="Valid email is required")

    if not data.company or not isinstance(data.company, str) or len(data.company.strip()) < 2:
        raise HTTPException(status_code=422, detail="Company must be a non-empty string with at least 2 characters")

    if not data.body or not isinstance(data.body, str) or len(data.body.strip()) < 10:
        raise HTTPException(status_code=422, detail="Body must be a non-empty string with at least 10 characters")

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)

        styles = getSampleStyleSheet()

        name_style = ParagraphStyle(
            "CoverName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT,
        )

        contact_style = ParagraphStyle(
            "CoverContact",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#4B5563"),
            alignment=TA_LEFT,
        )

        body_style = ParagraphStyle(
            "CoverBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#1F2937"),
            alignment=TA_JUSTIFY,
        )

        story = []

        story.append(Paragraph(data.name, name_style))
        story.append(Spacer(1, 4))

        contact_parts = []
        if data.email:
            contact_parts.append(data.email)
        if data.phone:
            contact_parts.append(data.phone)

        contact_str = "  |  ".join(contact_parts)
        story.append(Paragraph(contact_str, contact_style))
        story.append(Spacer(1, 15))

        date_str = data.date or datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(date_str, body_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph(f"To the hiring team at {data.company},", body_style))
        story.append(Spacer(1, 12))

        paragraphs = [p.strip() for p in data.body.split("\n\n") if p.strip()]
        for p in paragraphs:
            story.append(Paragraph(p.replace("\n", "<br/>"), body_style))
            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=cover_letter_{data.company.replace(' ', '_')}.pdf"},
        )
    except Exception as e:
        logger.error("Failed to generate cover letter PDF for user %s: %s", user.id, str(e))
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
