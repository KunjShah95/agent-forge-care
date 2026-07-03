"""Networking Agent prompt templates."""


def outreach_prompt(
    all_skills: list[str],
    role: str,
    target_companies: list[str],
    github_context: str,
    portfolio_context: str,
) -> str:
    """Build the LLM prompt for generating outreach messages."""
    companies_str = ", ".join(target_companies) if target_companies else "target companies"
    github_block = (
        "GITHUB EVIDENCE (reference these real projects as proof of skill):\n"
        f"{github_context}\n"
    ) if github_context else ""
    portfolio_block = (
        "PORTFOLIO EVIDENCE (reference these real projects and experience):\n"
        f"{portfolio_context}\n"
    ) if portfolio_context else ""
    skills_str = ", ".join(all_skills) if all_skills else "not specified"
    role_str = role or "not specified"

    return f"""You are a networking and outreach specialist.

USER CONTEXT:
- Skills: {skills_str}
- Target role: {role_str}
- Target companies: {companies_str}

{portfolio_block}{github_block}Generate outreach templates as a JSON object:
- "templates": array of objects, each with keys "type" ("cold_email" or "linkedin_message"), "subject" (string, empty for linkedin), "message" (string). Generate one cold_email and one linkedin_message per target company.
- "best_practices": array of 5 networking best practices (strings)

Messages should reference the user's actual skills, be concise, professional, and include a clear low-friction call to action.
If portfolio data is available, mention specific projects, role, and technologies from their portfolio.
If GitHub data is available, mention specific projects and languages from their GitHub profile.
Ground the message in concrete project evidence — never make up generic claims.
Return ONLY valid JSON. No markdown, no explanations."""
