from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:changeme@postgres:5432/vidpipeline"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # API Keys
    anthropic_api_key: str = ""
    assemblyai_api_key: str = ""
    shotstack_api_key: str = ""
    shotstack_env: str = "stage"   # "stage" or "v1" (production)

    # Storage
    storage_type: str = "local"          # "local" or "r2"
    local_storage_path: str = "/app/storage"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_url: str = ""              # e.g. https://pub-xxx.r2.dev

    # App limits
    max_file_size_mb: int = 500
    file_ttl_hours: int = 24
    max_shorts: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
