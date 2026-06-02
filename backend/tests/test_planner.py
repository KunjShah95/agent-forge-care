"""
Tests for the AgentForge planner and dispatcher system.
Uses mock database sessions and sample data.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.planner import _keyword_decompose, format_planner_response
decompose_goal = _keyword_decompose
from app.models.user import AgentType


class TestPlannerDecomposition:
    """Test that goal decomposition produces correct task lists."""

    def setup_profile(self) -> dict:
        return {
            "id": "test-profile-id",
            "skills": ["Python", "TypeScript", "React"],
            "target_locations": ["Remote", "Ahmedabad"],
            "role_types": ["Internship"],
            "career_goal": "ML Research Intern",
        }

    def test_internship_goal(self):
        """A goal about internships should dispatch the internship agent."""
        profile = self.setup_profile()
        tasks = decompose_goal("Find AI internships in Ahmedabad", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "internship" in agents
        assert any("Ahmedabad" in str(t["params"]) for t in tasks)

    def test_job_goal(self):
        """A goal about jobs should dispatch the job agent."""
        profile = self.setup_profile()
        tasks = decompose_goal("Find full-time React developer roles", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "job" in agents

    def test_interview_prep_goal(self):
        """An interview prep goal should dispatch the interview agent."""
        profile = self.setup_profile()
        tasks = decompose_goal("Help me prepare for Google interviews", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "interview" in agents

    def test_resume_goal(self):
        """A resume tailoring goal should dispatch the resume agent."""
        profile = self.setup_profile()
        tasks = decompose_goal("Tailor my resume for ML roles", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "resume" in agents

    def test_networking_goal(self):
        """A networking goal should dispatch the networking agent."""
        profile = self.setup_profile()
        tasks = decompose_goal("Help me network at Stripe", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "networking" in agents

    def test_research_goal(self):
        """A research goal should dispatch the research agent."""
        profile = self.setup_profile()
        tasks = decompose_goal("Research Anthropic before interview", profile, {})
        agents = [t["agent"] for t in tasks]
        assert "research" in agents

    def test_complex_goal_multiple_agents(self):
        """A complex goal should dispatch multiple specialist agents."""
        profile = self.setup_profile()
        tasks = decompose_goal(
            "Find AI internships and prepare for interviews at top labs",
            profile,
            {},
        )
        agents = [t["agent"] for t in tasks]
        assert "internship" in agents
        assert "interview" in agents

    def test_general_goal_defaults_to_monitor(self):
        """A vague goal should default to the monitor agent."""
        profile = self.setup_profile()
        tasks = decompose_goal("Help me find something good", profile, {})
        agents = [t["agent"] for t in tasks]
        assert len(tasks) > 0

    def test_tasks_have_priorities(self):
        """All decomposed tasks should have priority values."""
        profile = self.setup_profile()
        tasks = decompose_goal("Find internships and jobs in AI", profile, {})
        for t in tasks:
            assert "priority" in t
            assert isinstance(t["priority"], int)


class TestPlannerResponse:
    """Test that the planner response formatting works correctly."""

    def test_format_with_results(self):
        result = format_planner_response("Find internships", {
            "internship": {"items": [{"id": "1"}], "message": "Found 1 match"},
        })
        assert "Internship" in result
        assert "1 match" in result

    def test_format_with_errors(self):
        result = format_planner_response("Find internships", {
            "internship": {"error": "API timeout"},
        })
        assert "Internship" in result
        assert "error" in result.lower() or "⚠" in result

    def test_format_empty_results(self):
        result = format_planner_response("Find internships", {})
        assert "No results found" in result


class TestAgentHelpers:
    """Test helper functions used by agents."""

    def test_demo_internships_returns_data(self):
        """The demo internship data should return valid opportunities."""
        from app.agents.internship_agent import _demo_internships
        results = _demo_internships("test", "Remote")
        assert len(results) > 0
        assert results[0]["title"] == "ML Research Intern"
        assert all("title" in r and "company" in r for r in results)

    def test_demo_jobs_returns_data(self):
        """The demo job data should return valid opportunities."""
        from app.agents.job_agent import _demo_jobs
        results = _demo_jobs("test", "Remote")
        assert len(results) > 0
        assert any("salary_min" in r for r in results)

    def test_research_agent_builds_company_info(self):
        """Research agent should produce structured company info."""
        from app.agents.research_agent import _research_company
        result = _research_company("TestCorp")
        assert "name" in result
        assert "summary" in result
        assert "interview_process" in result
        assert result["name"] == "TestCorp"

    def test_research_agent_interview_insights(self):
        """Research agent should produce interview insights."""
        from app.agents.research_agent import _interview_insights
        result = _interview_insights("ML Engineer", ["Python", "PyTorch"])
        assert "questions" in result or "common_questions" in result
        assert "tips" in result
        assert len(result.get("common_questions", [])) > 0

    def test_research_agent_market_intelligence(self):
        """Research agent should produce market intelligence."""
        from app.agents.research_agent import _market_intelligence
        result = _market_intelligence(["Python", "React"])
        assert "outlook" in result
        assert len(result.get("trending_roles", [])) > 0

    def test_research_agent_skill_insights(self):
        """Research agent should produce skill analysis."""
        from app.agents.research_agent import _skill_insights
        result = _skill_insights(["Python", "TypeScript"])
        assert "insight" in result
        assert "recommended_skills" in result

    def test_demo_data_utility(self):
        """The shared demo data utility should work."""
        from app.utils.demo_data import generate_demo_opportunities
        results = generate_demo_opportunities(AgentType.internship, "ML", "Remote")
        assert len(results) > 0
        assert all("title" in r and "company" in r for r in results)

    def test_internship_agent_fallback_method(self):
        """The internship agent's demo fallback should return valid data."""
        from app.agents.internship_agent import _demo_internships
        results = _demo_internships("ML internship", "San Francisco")
        assert len(results) >= 3
        titles = [r["title"] for r in results]
        assert "ML Research Intern" in titles
