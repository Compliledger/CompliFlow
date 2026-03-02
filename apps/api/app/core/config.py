from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/compliflow"
    redis_url: str = "redis://localhost:6379/0"
    receipt_signing_private_key_b64: str = ""
    receipt_signing_public_key_b64: str = ""

    model_config = {"env_file": Path(__file__).parent.parent.parent / ".env"}


settings = Settings()
