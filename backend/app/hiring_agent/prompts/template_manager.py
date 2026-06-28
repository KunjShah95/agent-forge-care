import os
import logging
from pathlib import Path

logger = logging.getLogger("agentforge.hiring_agent.templates")

TEMPLATES_DIR = Path(__file__).parent / "templates"

_template_cache = {}


def _load_template(name: str) -> str | None:
    if name in _template_cache:
        return _template_cache[name]
    path = TEMPLATES_DIR / f"{name}.jinja"
    if not path.exists():
        logger.warning("Template not found: %s", path)
        return None
    try:
        content = path.read_text(encoding="utf-8")
        _template_cache[name] = content
        return content
    except Exception as e:
        logger.warning("Failed to load template %s: %s", name, e)
        return None


def render_template(section_name: str, **kwargs) -> str | None:
    template_str = _load_template(section_name)
    if template_str is None:
        return None
    try:
        result = template_str
        for key, value in kwargs.items():
            placeholder = "{{ " + key + " }}"
            result = result.replace(placeholder, str(value or ""))
        return result
    except Exception as e:
        logger.warning("Failed to render template %s: %s", section_name, e)
        return None
