"""
Agent configuration constants.
Centralizes all magic numbers, weights, limits, defaults, and collection names
that were previously hardcoded across agent handler files.
"""

# ── LLM Defaults ───────────────────────────────────────────

LLM_TEMPERATURE_CREATIVE = 0.7
LLM_TEMPERATURE_PRECISE = 0.5

# Task-to-provider routing: assign different providers to different agent tasks
# to spread rate-limit pressure across keys.
# "auto" = let model_manager pick best available via fallback chain.
LLM_PROVIDER_RESEARCH   = "groq"     # fast, free tier — good for research synthesis
LLM_PROVIDER_RESUME     = "mistral"  # strong instruction-following for doc generation
LLM_PROVIDER_INTERVIEW  = "groq"     # low-latency for interactive coaching
LLM_PROVIDER_NETWORKING = "mistral"  # nuanced tone for outreach writing
LLM_PROVIDER_DEFAULT    = "auto"     # fallback for anything else

# Legacy alias kept so old imports don't break — resolves to auto
LLM_PREFERRED_PROVIDER = "auto"

# ── Memory Weights ─────────────────────────────────────────

MEMORY_WEIGHT_HIGH = 0.9
MEMORY_WEIGHT_MEDIUM = 0.8
MEMORY_WEIGHT_LOW = 0.7

# ── Memory Keys (replaces hardcoded string literals) ───────

MEMORY_KEY_RESUME = "resume_tailoring"
MEMORY_KEY_INTERVIEW = "interview_prep"
MEMORY_KEY_NETWORKING = "last_networking"

# ── Vector Collection Names ────────────────────────────────

COLLECTION_RESUME = "resume_embeddings"
COLLECTION_MEMORY_NOTES = "memory_notes"

# ── Resume Agent Limits ────────────────────────────────────

MAX_RESUME_SUGGESTIONS = 7
MAX_RESUME_ACTION_ITEMS = 3
MAX_RESUME_ATS_KEYWORDS = 5
MAX_RESUME_PROJECTS = 3

# ── Interview Agent Limits ─────────────────────────────────

MAX_INTERVIEW_SKILLS = 5
MAX_INTERVIEW_PREP_TIPS = 5

# ── Networking Agent Limits ────────────────────────────────

MAX_NETWORKING_BEST_PRACTICES = 5
MAX_NETWORKING_PROJECTS = 3

# ── Default Parameter Values ───────────────────────────────

DEFAULT_ROLE_TYPE = "internship"
DEFAULT_COMPANY = "[Company]"
DEFAULT_ROLE = "[Role]"
