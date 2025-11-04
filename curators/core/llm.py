"""
LLM provider abstraction for curator agents.

Supports multiple providers: OpenAI, Google Gemini, Anthropic Claude.
"""

from typing import Optional
from langchain_core.language_models import BaseChatModel

from core.config import settings


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    **kwargs,
) -> BaseChatModel:
    """
    Get LLM instance based on configured provider.

    Args:
        provider: Override configured provider (openai, google, anthropic)
        model: Override configured model name
        temperature: Model temperature (default: 0.1 for deterministic)
        **kwargs: Additional provider-specific arguments

    Returns:
        LangChain chat model instance

    Raises:
        ValueError: If provider is not supported or API key missing
    """
    provider = provider or settings.llm_provider

    if provider == "openai":
        return _get_openai_llm(model, temperature, **kwargs)
    elif provider == "google":
        return _get_google_llm(model, temperature, **kwargs)
    elif provider == "anthropic":
        return _get_anthropic_llm(model, temperature, **kwargs)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported: openai, google, anthropic"
        )


def _get_openai_llm(
    model: Optional[str] = None,
    temperature: float = 0.1,
    **kwargs,
) -> BaseChatModel:
    """Get OpenAI chat model."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "OpenAI provider not installed. Install with: "
            "pip install -e '.[openai]'"
        )

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")

    return ChatOpenAI(
        model=model or settings.openai_model,
        temperature=temperature,
        api_key=settings.openai_api_key,
        **kwargs,
    )


def _get_google_llm(
    model: Optional[str] = None,
    temperature: float = 0.1,
    **kwargs,
) -> BaseChatModel:
    """Get Google Gemini chat model."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "Google provider not installed. Install with: "
            "pip install -e '.[google]'"
        )

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY not set in environment")

    return ChatGoogleGenerativeAI(
        model=model or settings.google_model,
        temperature=temperature,
        google_api_key=settings.google_api_key,
        **kwargs,
    )


def _get_anthropic_llm(
    model: Optional[str] = None,
    temperature: float = 0.1,
    **kwargs,
) -> BaseChatModel:
    """Get Anthropic Claude chat model."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "Anthropic provider not installed. Install with: "
            "pip install -e '.[anthropic]'"
        )

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")

    return ChatAnthropic(
        model=model or settings.anthropic_model,
        temperature=temperature,
        anthropic_api_key=settings.anthropic_api_key,
        **kwargs,
    )


def get_embeddings(provider: Optional[str] = None):
    """
    Get embeddings model for vector operations.

    Args:
        provider: Override configured provider

    Returns:
        LangChain embeddings instance
    """
    provider = provider or settings.llm_provider

    if provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            raise ImportError("OpenAI provider not installed")

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set")

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )

    elif provider == "google":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError:
            raise ImportError("Google provider not installed")

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        return GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.google_api_key,
        )

    else:
        # Fallback to OpenAI for embeddings
        raise ValueError(
            f"Embeddings not implemented for provider: {provider}. "
            f"Use 'openai' or 'google'"
        )


# Convenience exports
__all__ = ["get_llm", "get_embeddings"]
