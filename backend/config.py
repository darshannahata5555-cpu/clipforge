from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:changeme@postgres:5432/vidpipeline"

    # API Keys
    anthropic_api_key: str = ""
    assemblyai_api_key: str = ""

    # Storage
    storage_type: str = "local"          # "local" or "r2"
    local_storage_path: str = "/app/storage"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_url: str = ""

    # App limits
    max_file_size_mb: int = 500
    max_shorts: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
