"""
Work-mode helpers for the opportunity agents.

Two small pure functions shared by the job agent and the monitor scan:

- ``categorize_search_keyword`` maps a free-text keyword/role-type onto the
  ``SearchAdapter`` category selector ("job" / "internship"). The adapter only
  activates its job-board + LinkedIn scrapers when ``source_filter`` is exactly
  "job" or "internship", so callers must never pass raw query text there.

- ``infer_work_type`` derives the ``Opportunity.work_type`` value
  ("remote" / "hybrid" / "onsite") used by the Opportunities page filters,
  from the listing text plus the boolean ``remote`` flag.
"""

# Work-mode values understood by the frontend filters (Opportunities.tsx).
WORK_TYPE_REMOTE = "remote"
WORK_TYPE_HYBRID = "hybrid"
WORK_TYPE_ONSITE = "onsite"


def categorize_search_keyword(keyword: str) -> str:
    """
    Map a free-text keyword or role type onto a SearchAdapter category.

    Returns "internship" for intern/fellowship-style keywords, else "job".
    The result is always a valid ``source_filter`` so the adapter's job-board
    and LinkedIn scrapers actually run.
    """
    kw = (keyword or "").lower()
    if any(t in kw for t in ("intern", "fellowship", "co-op", "coop")):
        return "internship"
    return "job"


def infer_work_type(remote: bool, *texts: str | None) -> str | None:
    """
    Infer the work mode ("remote" / "hybrid" / "onsite") from listing text.

    ``remote`` is the boolean flag the search sources already set; ``texts`` are
    free-text fields (title, description, location). "hybrid" wins over "remote"
    because hybrid postings frequently also mention "remote". Returns ``None``
    when nothing in the text indicates a mode and ``remote`` is False, leaving
    the column NULL rather than guessing.
    """
    blob = " ".join(t for t in texts if t).lower()

    if "hybrid" in blob:
        return WORK_TYPE_HYBRID
    if remote or "remote" in blob or "work from home" in blob or "wfh" in blob:
        return WORK_TYPE_REMOTE
    if any(t in blob for t in ("on-site", "onsite", "on site", "in office", "in-office", "in person", "in-person")):
        return WORK_TYPE_ONSITE
    return None
