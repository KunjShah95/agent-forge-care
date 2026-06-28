import logging
import json
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

import pymupdf

from app.hiring_agent.schemas import ExtractedResume, ResumeBasics, ResumeWork, ResumeEducation, ResumeSkill, ResumeProject, ResumeAward
from app.hiring_agent.prompts.template_manager import render_template as _render_template

logger = logging.getLogger("agentforge.hiring_agent.pdf")


def _extract_pypdf_fallback(content: bytes) -> str:
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(content))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text.strip()


def _extract_text_with_pymupdf(content: bytes) -> str:
    doc = pymupdf.open(stream=content, filetype="pdf")
    try:
        pages = range(doc.page_count)
        from app.hiring_agent.pymupdf_rag import to_markdown
        resume_text = to_markdown(doc, pages=pages)
        return resume_text or ""
    except Exception as e:
        logger.warning("PyMuPDF RAG extraction failed, using basic: %s", e)
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def extract_pdf_text(content: bytes) -> str:
    try:
        return _extract_text_with_pymupdf(content)
    except Exception as e:
        logger.warning("PyMuPDF failed, falling back to pypdf: %s", e)
        return _extract_pypdf_fallback(content)


def _call_llm_section(llm_func, section_name: str, text_content: str, return_model_cls=None):
    try:
        prompt = _render_template(section_name, text_content=text_content)
        if not prompt:
            logger.error("Failed to render %s template", section_name)
            return None
        result = llm_func(section_name, prompt, return_model_cls)
        if result:
            return result
        return None
    except Exception as e:
        logger.error("Error extracting %s section: %s", section_name, e)
        return None


def parse_resume_sections(text_content: str, llm_call_fn) -> ExtractedResume:
    sections = ["basics", "work", "education", "skills", "projects", "awards"]
    section_models = {
        "basics": None,
        "work": None,
        "education": None,
        "skills": None,
        "projects": None,
        "awards": None,
    }

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(_call_llm_section, llm_call_fn, s, text_content): s
            for s in sections
        }
        for future in as_completed(future_map):
            section_name = future_map[future]
            try:
                section_data = future.result()
                if section_data:
                    section_models[section_name] = section_data
            except Exception as e:
                logger.warning("Section %s extraction failed: %s", section_name, e)

    resume = ExtractedResume(raw_text=text_content)

    if section_models.get("basics") and isinstance(section_models["basics"], dict):
        basics_data = section_models["basics"].get("basics", section_models["basics"])
        if isinstance(basics_data, dict):
            profiles = basics_data.get("profiles")
            if profiles and isinstance(profiles, list):
                cleaned = []
                for p in profiles:
                    if isinstance(p, dict) and "url" in p:
                        cleaned.append(p)
                    elif isinstance(p, str):
                        cleaned.append({"url": p, "network": p.split("/")[-2] if "github" in p.lower() else None})
                basics_data["profiles"] = cleaned or None
            resume.basics = ResumeBasics(**{
                "name": basics_data.get("name"),
                "email": basics_data.get("email"),
                "phone": basics_data.get("phone"),
                "url": basics_data.get("url"),
                "summary": basics_data.get("summary"),
                "location": basics_data.get("location"),
                "profiles": basics_data.get("profiles"),
            })

    if section_models.get("work") and isinstance(section_models["work"], dict):
        work_list = section_models["work"].get("work", [])
        if work_list and isinstance(work_list, list):
            resume.work = [
                ResumeWork(**{
                    "name": w.get("name"),
                    "position": w.get("position"),
                    "url": w.get("url"),
                    "startDate": str(w.get("startDate")) if w.get("startDate") else None,
                    "endDate": str(w.get("endDate")) if w.get("endDate") else None,
                    "summary": w.get("summary"),
                    "highlights": w.get("highlights"),
                })
                for w in work_list if isinstance(w, dict)
            ]

    if section_models.get("education") and isinstance(section_models["education"], dict):
        edu_list = section_models["education"].get("education", [])
        if edu_list and isinstance(edu_list, list):
            resume.education = [
                ResumeEducation(**{
                    "institution": e.get("institution"),
                    "area": e.get("area"),
                    "studyType": e.get("studyType"),
                    "startDate": str(e.get("startDate")) if e.get("startDate") else None,
                    "endDate": str(e.get("endDate")) if e.get("endDate") else None,
                    "score": e.get("score"),
                })
                for e in edu_list if isinstance(e, dict)
            ]

    if section_models.get("skills") and isinstance(section_models["skills"], dict):
        skills_list = section_models["skills"].get("skills", [])
        if skills_list and isinstance(skills_list, list):
            resume.skills = [
                ResumeSkill(**{
                    "name": s.get("name"),
                    "level": s.get("level"),
                    "keywords": s.get("keywords"),
                })
                for s in skills_list if isinstance(s, dict)
            ]

    if section_models.get("projects") and isinstance(section_models["projects"], dict):
        proj_list = section_models["projects"].get("projects", [])
        if proj_list and isinstance(proj_list, list):
            resume.projects = [
                ResumeProject(**{
                    "name": p.get("name"),
                    "description": p.get("description"),
                    "url": p.get("url"),
                    "technologies": p.get("technologies", p.get("skills")),
                    "highlights": p.get("highlights"),
                })
                for p in proj_list if isinstance(p, dict)
            ]

    if section_models.get("awards") and isinstance(section_models["awards"], dict):
        award_list = section_models["awards"].get("awards", [])
        if award_list and isinstance(award_list, list):
            resume.awards = [
                ResumeAward(**{
                    "title": a.get("title"),
                    "date": a.get("date"),
                    "awarder": a.get("awarder"),
                    "summary": a.get("summary"),
                })
                for a in award_list if isinstance(a, dict)
            ]

    return resume


def convert_resume_to_evaluation_text(resume: ExtractedResume, github_text: str = "", portfolio_text: str = "", live_demo_text: str = "") -> str:
    parts = []
    if resume.raw_text:
        parts.append(resume.raw_text)
    if resume.basics:
        parts.append(f"Candidate: {resume.basics.name or 'N/A'}")
        parts.append(f"Email: {resume.basics.email or 'N/A'}")
        if resume.basics.summary:
            parts.append(f"Summary: {resume.basics.summary}")
    if resume.work:
        for w in resume.work:
            parts.append(f"Work: {w.position or ''} at {w.name or ''} ({w.startDate or ''} - {w.endDate or ''})")
            if w.summary:
                parts.append(f"  {w.summary}")
            if w.highlights:
                for h in w.highlights:
                    parts.append(f"  - {h}")
    if resume.education:
        for e in resume.education:
            parts.append(f"Education: {e.studyType or ''} at {e.institution or ''}")
    if resume.skills:
        for s in resume.skills:
            if s.keywords:
                parts.append(f"Skill: {s.name or ''} - {', '.join(s.keywords)}")
            else:
                parts.append(f"Skill: {s.name or ''}")
    if resume.projects:
        for p in resume.projects:
            parts.append(f"Project: {p.name or ''}")
            if p.description:
                parts.append(f"  {p.description}")
            if p.technologies:
                parts.append(f"  Tech: {', '.join(p.technologies)}")
    if resume.awards:
        for a in resume.awards:
            parts.append(f"Award: {a.title or ''} ({a.awarder or ''})")
    if github_text:
        parts.append(github_text)
    if portfolio_text:
        parts.append(portfolio_text)
    if live_demo_text:
        parts.append(live_demo_text)
    return "\n".join(parts)
