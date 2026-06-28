def transform_parsed_data(parsed_data: dict) -> dict:
    if not isinstance(parsed_data, dict):
        return parsed_data
    if "basics" in parsed_data and len(parsed_data) > 1:
        return {
            "basics": _transform_basics(parsed_data.get("basics", {})),
            "work": _transform_work(parsed_data.get("work", parsed_data.get("work_experience", parsed_data.get("experience", [])))),
            "education": _transform_education(parsed_data.get("education", [])),
            "awards": _transform_awards(parsed_data.get("awards", parsed_data.get("achievements", parsed_data.get("honors_and_awards", [])))),
            "skills": _transform_skills(parsed_data),
            "projects": _transform_projects(parsed_data),
        }
    return parsed_data


def _transform_basics(data: dict) -> dict:
    return {
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "url": data.get("url"),
        "summary": data.get("summary"),
        "location": data.get("location"),
        "profiles": data.get("profiles", []),
    }


def _transform_work(data: list) -> list:
    if not isinstance(data, list):
        return []
    return [
        {
            "name": w.get("name"),
            "position": w.get("position"),
            "url": w.get("url"),
            "startDate": w.get("startDate"),
            "endDate": w.get("endDate"),
            "summary": w.get("summary"),
            "highlights": w.get("highlights", []),
        }
        for w in data if isinstance(w, dict)
    ]


def _transform_education(data: list) -> list:
    if not isinstance(data, list):
        return []
    return [
        {
            "institution": e.get("institution"),
            "area": e.get("area"),
            "studyType": e.get("studyType"),
            "startDate": e.get("startDate"),
            "endDate": e.get("endDate"),
            "score": e.get("score"),
        }
        for e in data if isinstance(e, dict)
    ]


def _transform_awards(data: list) -> list:
    if not isinstance(data, list):
        return []
    return [
        {
            "title": a.get("title"),
            "date": a.get("date"),
            "awarder": a.get("awarder"),
            "summary": a.get("summary"),
        }
        for a in data if isinstance(a, dict)
    ]


def _transform_skills(data: dict) -> list:
    skills = data.get("skills", [])
    if isinstance(skills, list):
        return [
            {
                "name": s.get("name"),
                "level": s.get("level"),
                "keywords": s.get("keywords", []),
            }
            for s in skills if isinstance(s, dict)
        ]
    return []


def _transform_projects(data: dict) -> list:
    projects = data.get("projects", data.get("projectsOpenSource", []))
    if not isinstance(projects, list):
        return []
    return [
        {
            "name": p.get("name"),
            "description": p.get("description"),
            "url": p.get("url"),
            "technologies": p.get("technologies", p.get("skills", [])),
            "highlights": p.get("highlights", []),
        }
        for p in projects if isinstance(p, dict)
    ]


def convert_json_resume_to_text(data) -> str:
    parts = []
    basics = getattr(data, "basics", None) or (data.get("basics") if isinstance(data, dict) else None)
    if basics:
        name = basics.get("name") if isinstance(basics, dict) else getattr(basics, "name", None)
        email = basics.get("email") if isinstance(basics, dict) else getattr(basics, "email", None)
        summary = basics.get("summary") if isinstance(basics, dict) else getattr(basics, "summary", None)
        if name:
            parts.append(f"Name: {name}")
        if email:
            parts.append(f"Email: {email}")
        if summary:
            parts.append(f"Summary: {summary}")

    for attr in ["work", "education", "projects", "skills", "awards"]:
        items = getattr(data, attr, None) if not isinstance(data, dict) else data.get(attr)
        if items and isinstance(items, list):
            parts.append(f"\n{attr.upper()}:")
            for item in items:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("institution") or item.get("position") or item.get("title", "")
                    parts.append(f"  - {name}")
                else:
                    parts.append(f"  - {item}")

    return "\n".join(parts)
