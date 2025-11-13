from pathlib import Path

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    # LLM configuration
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str
    # Observability configuration
    otel_exporter_endpoint: str = "http://localhost:4317"
    service_name: str = "ragbits-simple_agent"
    enable_tracing: bool = True
    enable_metrics: bool = True

    class Config:
        env_file = Path(__file__).parent.parent.parent / ".env"


config = AppConfig()