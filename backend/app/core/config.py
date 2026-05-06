from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_platform"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GPTZERO_API_KEY: str = ""
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    DEFAULT_AGENT_TIMEOUT: int = 120
    DEFAULT_MAX_ITERATIONS: int = 3
    DEFAULT_AI_RATE_THRESHOLD: float = 70.0
    DEFAULT_MEMORY_TOP_K: int = 5
    DEFAULT_MEMORY_TTL_DAYS: int = 90
    OPENAI_BASE_URL: str = ""
    ANTHROPIC_BASE_URL: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
