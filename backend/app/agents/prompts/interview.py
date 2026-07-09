"""Interview Agent prompt templates."""


def prepare_interview_prompt(
    all_skills: list[str],
    role_type: str,
    company: str | None,
    github_context: str,
    portfolio_context: str,
) -> str:
    """Build the LLM prompt for interview preparation."""
    github_block = (
        (f"GITHUB EVIDENCE (use these real projects for technical skill questions):\n{github_context}\n")
        if github_context
        else ""
    )
    portfolio_block = (
        (f"PORTFOLIO EVIDENCE (use these real projects for behavioral questions):\n{portfolio_context}\n")
        if portfolio_context
        else ""
    )
    skills_str = ", ".join(all_skills) if all_skills else "not specified"
    company_str = company or "not specified"

    return f"""You are an interview preparation expert.

USER CONTEXT:
- Skills: {skills_str}
- Target role type: {role_type}
- Target company: {company_str}

{portfolio_block}{github_block}Generate interview preparation materials as a JSON object:
- "questions": array of objects, each with keys "skill" (string), "question" (string), "type" ("behavioral" or "technical"), "tips" (string). Generate 2 questions per skill (one behavioral, one technical) for up to 5 skills, plus 3 general behavioral questions with skill set to "general".
- "prep_tips": array of 5 specific preparation tips referencing the user's actual skills and target company

Make questions realistic and tailored to the user's skills and target role.
If portfolio data is available, reference specific projects and experience in the question examples.
If GitHub data is available, reference specific repos and languages in technical questions.
Ground questions in real project evidence — make them feel like they come from a real code review or portfolio walkthrough.
Return ONLY valid JSON. No markdown, no explanations."""


def review_answer_prompt(
    question: str,
    answer: str,
    company: str | None,
    role: str | None,
) -> str:
    """Build the LLM prompt for reviewing interview answers."""
    company_line = f"COMPANY: {company}\n" if company else ""
    role_line = f"ROLE: {role}\n" if role else ""

    return f"""You are an expert interview coach. Review this answer and provide structured feedback.

QUESTION: {question}

ANSWER: {answer}

{company_line}{role_line}Return ONLY valid JSON with these keys:
- "feedback": A 2-3 sentence constructive critique of the answer
- "score": An integer 0-100 rating
- "strengths": Array of 1-3 specific strengths in the answer
- "improvements": Array of 1-3 specific improvements or gaps

Be specific and actionable. Reference what the candidate actually said.
Return ONLY valid JSON. No markdown, no explanations."""
