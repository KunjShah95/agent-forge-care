"""Resume Agent prompt templates."""


def tailor_resume_prompt(
    all_skills: list[str],
    role_type: str,
    target_company: str | None,
    github_context: str,
    portfolio_context: str,
    ha_block: str,
) -> str:
    """Build the LLM prompt for resume tailoring."""
    github_block = (
        "GITHUB EVIDENCE (use this to ground suggestions in real projects):\n"
        f"{github_context}\n"
    ) if github_context else ""
    portfolio_block = (
        "PORTFOLIO EVIDENCE (use this to reference real projects and experience):\n"
        f"{portfolio_context}\n"
    ) if portfolio_context else ""
    skills_str = ", ".join(all_skills) if all_skills else "not specified"
    company_str = target_company or "not specified"

    return f"""You are a career advisor AI that helps users tailor their resumes.

USER CONTEXT:
- Skills: {skills_str}
- Target role type: {role_type}
- Target company: {company_str}

{github_block}{portfolio_block}Generate resume tailoring suggestions as a JSON object with these keys:
- "suggestions": array of 7 specific, actionable resume suggestions (strings)
- "action_items": array of 3 concrete next steps (strings)

Make suggestions specific to the user's skills and target role. Reference their actual skills by name.
If GitHub data is available, mention specific projects, languages, and starred repos as evidence of skill proficiency.
If portfolio data is available, mention specific projects, technologies, and experience from the portfolio.
Return ONLY valid JSON. No markdown, no explanations."""


def cover_letter_prompt(
    all_skills: list[str],
    role: str,
    company: str,
    school: str | None,
    github_context: str,
    portfolio_context: str,
    ha_block: str,
) -> str:
    """Build the LLM prompt for cover letter generation."""
    portfolio_block = (
        "PORTFOLIO EVIDENCE (reference these real projects and experience):\n"
        f"{portfolio_context}\n"
    ) if portfolio_context else ""
    github_block = (
        "GITHUB EVIDENCE (reference these real projects as proof of skill):\n"
        f"{github_context}\n"
    ) if github_context else ""
    skills_str = ", ".join(all_skills) if all_skills else "not specified"
    school_str = school or "not specified"

    return f"""You are a professional cover letter writer.

USER CONTEXT:
- School/Background: {school_str}
- Skills: {skills_str}
- Target company: {company}
- Target role: {role}

{portfolio_block}{github_block}{ha_block}Generate a compelling, professional cover letter and customization tips as a JSON object:
- "cover_letter": a full cover letter string (3-4 paragraphs, with greeting and sign-off using [Your Name])
- "customization_tips": array of 3 specific tips for personalizing this letter

The letter should reference the user's actual skills by name, show enthusiasm for the company, and be specific to the role.
If portfolio data is available, mention specific projects, role, and technologies from their portfolio.
If GitHub data is available, mention specific projects and languages from their GitHub profile.
Ground the letter in concrete project evidence — never make up generic claims.
Return ONLY valid JSON. No markdown, no explanations."""
