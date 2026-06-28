"""
AI Model Manager — unified multi-provider LLM and Embeddings gateway.

Provides a single interface for all AI model operations across the agent system:
- LLM chat completion (with automatic fallback chain)
- Text embeddings (with automatic fallback chain)
- Configurable provider priority
- Auto-detection of available API keys

Supported LLM Providers (in fallback order):
  1. OpenAI           (paid)          — GPT-4o, GPT-4o-mini
  2. Anthropic        (paid)          — Claude 3.5 Sonnet, Claude 3 Haiku
  3. Google Gemini    (free tier)     — Gemini 1.5/2.0 Pro, Flash
  4. DeepSeek         (paid)          — DeepSeek-V4-Flash, DeepSeek-V4-Pro
  5. Groq             (free tier)     — Llama 3, Mixtral, Gemma (fast)
  6. Mistral AI       (free tier)     — Mistral Large, Small, Codestral
  7. Together AI      (paid)          — Llama, Qwen, DeepSeek, Mistral
  8. Fireworks AI     (free $1 trial) — Llama, Qwen, DeepSeek, Mistral
  9. OpenRouter       (free tier)     — Gateway to 200+ models
 10. Ollama           (free, local)   — Llama, Mistral, Qwen, DeepSeek

Supported Embedding Providers (in fallback order):
  1. OpenAI           (paid)          — text-embedding-3-small/3-large
  2. Google Gemini    (free tier)     — gemini-embedding-001
  3. HuggingFace      (free, local)   — all-mpnet-base-v2, BGE, etc.
  4. Ollama           (free, local)   — nomic-embed-text, mxbai-embed-large
  5. Hash Fallback    (free, local)   — Deterministic fallback (dev/demo only)
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("agentforge.model_manager")


# ─── Provider Availability ──────────────────────────────────


def get_available_llm_providers() -> list[dict]:
    """Return all available LLM providers with their config, sorted by priority."""
    providers = []

    # 1. OpenAI (highest priority)
    if settings.openai_api_key:
        providers.append({
            "name": "openai",
            "priority": 1,
            "display": "OpenAI",
            "api_key": settings.openai_api_key,
            "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o3-mini", "o1-mini"],
        })

    # 2. Anthropic
    if settings.anthropic_api_key:
        providers.append({
            "name": "anthropic",
            "priority": 2,
            "display": "Anthropic",
            "api_key": settings.anthropic_api_key,
            "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        })

    # 3. Google Gemini
    if settings.google_api_key:
        providers.append({
            "name": "gemini",
            "priority": 3,
            "display": "Google Gemini",
            "api_key": settings.google_api_key,
            "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        })

    # 4. DeepSeek (very cheap, open-source reasoning)
    if settings.deepseek_api_key:
        providers.append({
            "name": "deepseek",
            "priority": 4,
            "display": "DeepSeek",
            "api_key": settings.deepseek_api_key,
            "models": ["deepseek-chat", "deepseek-reasoner"],
        })

    # 5. Groq (free tier)
    if settings.groq_api_key:
        providers.append({
            "name": "groq",
            "priority": 5,
            "display": "Groq",
            "api_key": settings.groq_api_key,
            "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        })

    # 6. Mistral AI
    if settings.mistral_api_key:
        providers.append({
            "name": "mistral",
            "priority": 6,
            "display": "Mistral AI",
            "api_key": settings.mistral_api_key,
            "models": ["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
        })

    # 7. Together AI (OpenAI-compatible, wide open-source model catalog)
    if settings.together_api_key:
        providers.append({
            "name": "together",
            "priority": 7,
            "display": "Together AI",
            "api_key": settings.together_api_key,
            "models": ["meta-llama/Meta-Llama-3.1-8B-Instruct", "meta-llama/Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct-Turbo"],
        })

    # 8. Fireworks AI (OpenAI-compatible, $1 free credits)
    if settings.fireworks_api_key:
        providers.append({
            "name": "fireworks",
            "priority": 8,
            "display": "Fireworks AI",
            "api_key": settings.fireworks_api_key,
            "models": ["accounts/fireworks/models/deepseek-v3p1", "accounts/fireworks/models/llama-v3p3-70b-instruct", "accounts/fireworks/models/qwen3-235b-a22b"],
        })

    # 9. OpenRouter (gateway)
    if settings.openrouter_api_key:
        providers.append({
            "name": "openrouter",
            "priority": 9,
            "display": "OpenRouter",
            "api_key": settings.openrouter_api_key,
            "models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-haiku", "google/gemini-2.0-flash-001", "meta-llama/llama-3.3-70b-instruct"],
        })

    # 10. Ollama (free, local — always available if running)
    providers.append({
        "name": "ollama",
        "priority": 10,
        "display": "Ollama (Local)",
        "base_url": settings.ollama_base_url,
        "api_key": "",  # no key needed
        "models": ["llama3.2", "llama3.1", "mistral", "qwen2.5", "deepseek-coder"],
    })

    return providers


def get_available_embedding_providers() -> list[dict]:
    """Return all available embedding providers with their config, sorted by priority."""
    providers = []

    # 1. OpenAI (highest priority)
    if settings.openai_api_key:
        providers.append({
            "name": "openai",
            "priority": 1,
            "display": "OpenAI",
            "api_key": settings.openai_api_key,
            "models": ["text-embedding-3-small", "text-embedding-3-large"],
            "dimensions": 1536,
        })

    # 2. Google Gemini
    if settings.google_api_key:
        providers.append({
            "name": "gemini",
            "priority": 2,
            "display": "Google Gemini",
            "api_key": settings.google_api_key,
            "models": ["gemini-embedding-001"],
            "dimensions": 768,
        })

    # 3. HuggingFace (free, local)
    providers.append({
        "name": "huggingface",
        "priority": 3,
        "display": "HuggingFace",
        "api_key": settings.huggingface_api_key,
        "models": ["sentence-transformers/all-mpnet-base-v2", "BAAI/bge-small-en-v1.5"],
        "dimensions": 768,
    })

    # 4. Ollama (free, local)
    providers.append({
        "name": "ollama",
        "priority": 4,
        "display": "Ollama (Local)",
        "base_url": settings.ollama_base_url,
        "models": ["nomic-embed-text", "mxbai-embed-large"],
        "dimensions": 768,
    })

    return providers


def log_available_providers():
    """Log which providers are available at startup."""
    llm_providers = get_available_llm_providers()
    embedding_providers = get_available_embedding_providers()

    available_llm = [p["display"] for p in llm_providers if p["name"] != "ollama" or True]
    available_emb = [p["display"] for p in embedding_providers if p["name"] not in ("huggingface", "ollama")]

    logger.info(
        "AI Model Manager initialized. LLM providers: %s | Embedding providers: %s",
        ", ".join(p["display"] for p in llm_providers),
        ", ".join(p["display"] for p in embedding_providers),
    )

    if not settings.openai_api_key and not settings.google_api_key:
        logger.warning(
            "No cloud embedding provider configured. "
            "Falling back to local HuggingFace/Ollama embeddings. "
            "For best results, set OPENAI_API_KEY or GOOGLE_API_KEY."
        )


# ─── LLM Chat Model ─────────────────────────────────────────


def _build_llm_instance(provider: dict, model: str, temperature: float = 0.7):
    """
    Build a LangChain chat model instance for the given provider.
    Returns None if the provider's package is not installed.
    """
    name = provider["name"]

    try:
        if name == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
            )

        elif name == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
            )

        elif name == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
            )

        elif name == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
            )

        elif name == "mistral":
            from langchain_mistralai import ChatMistralAI
            return ChatMistralAI(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
            )

        elif name == "deepseek":
            # DeepSeek has official langchain-deepseek package
            try:
                from langchain_deepseek import ChatDeepSeek
                return ChatDeepSeek(
                    model=model,
                    temperature=temperature,
                    api_key=provider["api_key"],
                )
            except ImportError:
                # Fallback: DeepSeek uses OpenAI-compatible API
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    api_key=provider["api_key"],
                    base_url="https://api.deepseek.com",
                )

        elif name == "together":
            # Together AI uses OpenAI-compatible API
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
                base_url="https://api.together.xyz/v1",
            )

        elif name == "fireworks":
            # Fireworks AI uses OpenAI-compatible API
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
                base_url="https://api.fireworks.ai/inference/v1",
            )

        elif name == "openrouter":
            # OpenRouter uses OpenAI-compatible API
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=provider["api_key"],
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://agentforge.ai",
                    "X-Title": "AgentForge Career OS",
                },
            )

        elif name == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model,
                temperature=temperature,
                base_url=provider.get("base_url", "http://localhost:11434"),
            )

    except ImportError as e:
        logger.warning(
            "Package not installed for provider '%s': %s. Skipping.", name, e
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to initialize provider '%s' model '%s': %s", name, model, e
        )
        return None

    return None


def get_chat_model(
    temperature: float = 0.7,
    preferred_provider: Optional[str] = None,
) -> Optional[object]:
    """
    Get the best available LangChain chat model with fallback chain.

    If preferred_provider is set (e.g. "openai", "anthropic"), that provider
    is tried first. Otherwise, providers are tried in priority order.
    Falls back through all available providers.

    Returns a LangChain Runnable (ChatModel) with .with_fallbacks() configured,
    or None if no provider is available at all.
    """
    providers = get_available_llm_providers()

    # Sort preferred provider to front if specified
    if preferred_provider:
        providers.sort(key=lambda p: 0 if p["name"] == preferred_provider else p["priority"])

    if not providers:
        logger.warning("No LLM providers available. No API keys configured.")
        return None

    # Build primary model (first available provider)
    primary_config = providers[0]
    primary_model = primary_config["models"][0]

    # For Ollama, prefer smaller models for speed
    if primary_config["name"] == "ollama":
        primary_model = "llama3.2"

    primary = _build_llm_instance(primary_config, primary_model, temperature)
    if primary is None and len(providers) == 1:
        return None

    # Build fallbacks from remaining providers
    fallbacks = []
    for prov in providers[1:]:
        # Pick the best model for each provider
        model = prov["models"][0]

        # For Ollama, prefer smaller/faster models
        if prov["name"] == "ollama":
            model = "llama3.2"

        instance = _build_llm_instance(prov, model, temperature)
        if instance is not None:
            fallbacks.append(instance)

    if primary is None and fallbacks:
        # Primary failed but we have fallbacks — use first fallback as primary
        primary = fallbacks.pop(0)

    if primary is None:
        logger.warning("All LLM providers failed to initialize.")
        return None

    # Only use with_fallbacks if we have fallbacks
    if fallbacks:
        logger.info(
            "LLM chain: primary=%s (%s), %d fallback(s): %s",
            primary_config["display"],
            primary_model,
            len(fallbacks),
            ", ".join(p["display"] for p in providers[1 : 1 + len(fallbacks)]),
        )
        return primary.with_fallbacks(fallbacks)

    logger.info("LLM: using single provider %s (%s)", primary_config["display"], primary_model)
    return primary


def get_completion_llm(temperature: float = 0.7, preferred_provider: Optional[str] = None):
    """
    Convenience alias for get_chat_model().
    Used by agents to replace their old _get_llm() functions.
    """
    return get_chat_model(temperature=temperature, preferred_provider=preferred_provider)


# ─── Embedding Model ────────────────────────────────────────


def _build_embedding_instance(provider: dict, model: str):
    """Build a LangChain embedding model instance for the given provider."""
    name = provider["name"]

    try:
        if name == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=model,
                api_key=provider["api_key"],
            )

        elif name == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                model=model,
                google_api_key=provider["api_key"],
            )

        elif name == "huggingface":
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name=model,
                encode_kwargs={"normalize_embeddings": True},
            )

        elif name == "ollama":
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                model=model,
                base_url=provider.get("base_url", "http://localhost:11434"),
            )

    except ImportError as e:
        logger.warning(
            "Package not installed for embedding provider '%s': %s. Skipping.", name, e
        )
        return None
    except Exception as e:
        logger.warning(
            "Failed to initialize embedding provider '%s' model '%s': %s", name, model, e
        )
        return None

    return None


_embedding_instance = None


def get_embeddings():
    """
    Get the best available embedding model with fallback chain.
    Caches the successful instance for reuse.

    Returns a LangChain Embeddings object, or None if no provider is available.
    """
    global _embedding_instance

    if _embedding_instance is not None:
        return _embedding_instance

    providers = get_available_embedding_providers()

    for prov in providers:
        model = prov["models"][0]

        # For Ollama, use the embedding model
        if prov["name"] == "ollama":
            model = "nomic-embed-text"

        instance = _build_embedding_instance(prov, model)
        if instance is not None:
            _embedding_instance = instance
            logger.info(
                "Embeddings: using %s (%s) — %d dimensions",
                prov["display"],
                model,
                prov.get("dimensions", 768),
            )
            return instance

    logger.warning("No embedding providers available. Will use hash-based fallback.")
    return None


def get_embedding_dimensions() -> int:
    """Return the dimensions of the current embedding model."""
    providers = get_available_embedding_providers()
    if providers:
        return providers[0].get("dimensions", 768)
    return 384  # Default fallback dimension

# ─── Startup Logging ────────────────────────────────────────

# Log available providers at import time
log_available_providers()
