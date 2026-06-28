"""Unit tests for the work-mode helpers used by the job/monitor agents."""

from app.utils.work_mode import categorize_search_keyword, infer_work_type


class TestCategorizeSearchKeyword:
    def test_internship_keywords(self):
        assert categorize_search_keyword("Internship") == "internship"
        assert categorize_search_keyword("ML Research Intern") == "internship"
        assert categorize_search_keyword("Summer Fellowship") == "internship"
        assert categorize_search_keyword("co-op") == "internship"

    def test_job_keywords(self):
        assert categorize_search_keyword("Full-time") == "job"
        assert categorize_search_keyword("software engineer") == "job"
        assert categorize_search_keyword("data scientist") == "job"
        assert categorize_search_keyword("") == "job"

    def test_result_is_valid_source_filter(self):
        # Must always be one of the categories the SearchAdapter scrapers honor.
        for kw in ["anything", "machine learning", "Intern", ""]:
            assert categorize_search_keyword(kw) in ("job", "internship")


class TestInferWorkType:
    def test_hybrid_wins_over_remote(self):
        assert infer_work_type(True, "Hybrid role, some remote days") == "hybrid"

    def test_remote_from_flag(self):
        assert infer_work_type(True, "Software Engineer", "NYC") == "remote"

    def test_remote_from_text(self):
        assert infer_work_type(False, "Remote — work from anywhere") == "remote"

    def test_onsite(self):
        assert infer_work_type(False, "On-site in Austin, TX") == "onsite"
        assert infer_work_type(False, "In-person, San Francisco") == "onsite"

    def test_unknown_stays_none(self):
        assert infer_work_type(False, "Software Engineer", "Austin, TX") is None

    def test_handles_none_fields(self):
        assert infer_work_type(False, None, None) is None
