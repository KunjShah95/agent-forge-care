"""
Shared demo data for the agent system.

Pulled out of graph.py to break the circular import:
  graph.py → assistant_agent.py → graph.py

All agent files can import from here safely.
"""

from app.models.user import AgentType


def generate_demo_opportunities(agent_type: AgentType, query: str, location: str | None) -> list[dict]:
    """Generate demo opportunities when search APIs are unavailable."""
    demos = {
        AgentType.internship: [
            {"title": "ML Research Intern", "company": "Anthropic", "type": "Internship",
             "location": "San Francisco, CA", "remote": True, "skills": ["Python", "PyTorch", "NLP"],
             "description": "Work on frontier AI safety research with world-class researchers.",
             "apply_url": "https://anthropic.com/careers"},
            {"title": "Software Engineer Intern", "company": "Stripe", "type": "Internship",
             "location": "Remote", "remote": True, "skills": ["TypeScript", "React", "Python"],
             "description": "Build payment infrastructure used by millions.",
             "apply_url": "https://stripe.com/jobs"},
            {"title": "Frontend Engineer Intern", "company": "Vercel", "type": "Internship",
             "location": "Remote", "remote": True, "skills": ["React", "Next.js", "TypeScript"],
             "description": "Help build the platform that powers the modern web.",
             "apply_url": "https://vercel.com/careers"},
            {"title": "Data Engineering Intern", "company": "Databricks", "type": "Internship",
             "location": "San Francisco, CA", "remote": True, "skills": ["Python", "SQL", "Spark"],
             "description": "Build data pipelines for the lakehouse platform.",
             "apply_url": "https://databricks.com/careers"},
            {"title": "Mobile Engineering Intern", "company": "Spotify", "type": "Internship",
             "location": "New York, NY", "remote": False, "skills": ["Kotlin", "Swift", "Mobile"],
             "description": "Build features for millions of music listeners worldwide.",
             "apply_url": "https://spotify.com/jobs"},
        ],
        AgentType.job: [
            {"title": "Software Engineer, New Grad", "company": "Google", "type": "Full-time",
             "location": "Multiple", "remote": False, "skills": ["Python", "C++", "Algorithms"],
             "description": "Build products used by billions globally.", "apply_url": "https://google.com/careers"},
            {"title": "Product Engineer", "company": "Linear", "type": "Full-time",
             "location": "New York", "remote": False, "skills": ["React", "TypeScript", "Design"],
             "description": "Build the most loved issue tracking tool.", "apply_url": "https://linear.app/jobs"},
            {"title": "Founding Engineer", "company": "Helia Labs", "type": "Full-time",
             "location": "San Francisco", "remote": True, "skills": ["Full-stack", "AI", "TypeScript"],
             "description": "Early-stage AI startup.", "apply_url": "https://helia.dev/jobs"},
            {"title": "ML Engineer", "company": "OpenAI", "type": "Full-time",
             "location": "San Francisco", "remote": False, "skills": ["Python", "PyTorch", "ML", "Distributed Systems"],
             "description": "Develop and deploy cutting-edge AI models.", "apply_url": "https://openai.com/careers"},
            {"title": "DevTools Engineer", "company": "GitHub", "type": "Full-time",
             "location": "Remote", "remote": True, "skills": ["Ruby", "Go", "API Design"],
             "description": "Build the platform that powers developer collaboration.", "apply_url": "https://github.com/careers"},
        ],
        AgentType.monitor: [
            {"title": "AI Safety Fellowship", "company": "MATS Program", "type": "Fellowship",
             "location": "Berkeley, CA", "remote": False, "skills": ["Research", "Alignment", "Python"],
             "description": "Intensive research program.", "apply_url": "https://matsprogram.org"},
            {"title": "NSF REU - Computer Vision", "company": "MIT CSAIL", "type": "Research",
             "location": "Cambridge, MA", "remote": False, "skills": ["CV", "Python", "Research"],
             "description": "Summer research program.", "apply_url": "https://mit.edu/csail/reu"},
            {"title": "Google Summer of Code", "company": "Google", "type": "Internship",
             "location": "Remote", "remote": True, "skills": ["Open-source", "Python", "C++"],
             "description": "Contributing to open-source projects.", "apply_url": "https://summerofcode.withgoogle.com"},
            {"title": "HackNY Fellowship", "company": "HackNY", "type": "Fellowship",
             "location": "New York, NY", "remote": False, "skills": ["Full-stack", "Startups", "Python"],
             "description": "Summer fellowship placing students at NYC startups.", "apply_url": "https://hackny.org"},
            {"title": "ML Alignment Theory Scholars", "company": "ARENA", "type": "Research",
             "location": "Remote", "remote": True, "skills": ["Math", "ML Theory", "Python"],
             "description": "Advanced research training in mechanistic interpretability.", "apply_url": "https://arena.org"},
        ],
    }
    return demos.get(agent_type, demos[AgentType.monitor])
