import os
import logging

logger = logging.getLogger("agentforge.opportunity_agent.templates")

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def load_template(name: str) -> str:
    path = os.path.join(_TEMPLATE_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("Template not found: %s", path)
        return ""


def render_template(template: str, **kwargs) -> str:
    """Simple template renderer using Python format strings (no Jinja2 dependency needed)."""
    for key, val in kwargs.items():
        placeholder = "{{ " + key + " }}"
        template = template.replace(placeholder, str(val))
    return template
