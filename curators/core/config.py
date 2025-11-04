"""
Configuration management for curator agents using Pydantic settings.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CuratorSettings(BaseSettings):
    """Global configuration for curator agents."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(..., description="Supabase service role key")

    # LLM Provider Selection
    llm_provider: str = Field(
        default="openai", description="LLM provider: openai, google, anthropic"
    )

    # OpenAI
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-5-nano", description="OpenAI model to use")

    # Google Gemini
    google_api_key: Optional[str] = Field(None, description="Google AI API key")
    google_model: str = Field(default="gemini-2.5-flash", description="Gemini model to use")

    # Anthropic Claude
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", description="Claude model to use")

    # Mem0 Memory System
    mem0_api_key: Optional[str] = Field(None, description="Mem0 API key (if using hosted)")
    mem0_config_path: Optional[str] = Field(
        default="config/mem0_config.json", description="Path to Mem0 configuration"
    )

    # Redis (for rate limiting & caching)
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(None, description="Redis password")

    # AWS S3 (for DeepAgents persistence)
    aws_access_key_id: Optional[str] = Field(None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS secret key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    s3_bucket_memories: str = Field(
        default="curator-memories", description="S3 bucket for memories"
    )
    s3_bucket_workflows: str = Field(
        default="curator-workflows", description="S3 bucket for workflows"
    )

    # Token Budget Management
    daily_token_limit: int = Field(
        default=1_000_000, description="Daily token limit per curator"
    )
    token_buffer_percentage: float = Field(
        default=0.1, description="Reserve 10% of budget for critical operations"
    )

    # Rate Limiting
    api_rate_limit_per_second: float = Field(
        default=0.5, description="Max API requests per second"
    )
    max_retry_attempts: int = Field(default=3, description="Max retry attempts for API calls")
    exponential_backoff_base: int = Field(default=2, description="Base for exponential backoff")

    # Progress Monitoring
    progress_update_interval: int = Field(
        default=5, description="Seconds between progress updates"
    )

    # Image Processing
    image_max_size_mb: int = Field(default=5, description="Max image size in MB")
    thumbnail_size: int = Field(default=300, description="Thumbnail size in pixels")
    thumbnail_quality: int = Field(default=85, description="WebP quality (1-100)")

    # DeepAgents
    deepagents_base_path: str = Field(
        default="/tmp/curator_agents", description="Base path for DeepAgents storage"
    )

    # LangGraph Platform
    langgraph_url: str = Field(
        default="http://localhost:8000", description="LangGraph Platform URL"
    )


# Global settings instance
settings = CuratorSettings()
