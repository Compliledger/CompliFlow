from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    port: int = 8000
    database_url: str = "sqlite:///./compliflow.db"
    redis_url: str = "redis://localhost:6379/0"
    receipt_signing_private_key_b64: str = ""
    receipt_signing_public_key_b64: str = ""
    
    yellow_app_id: str = "APP-4720-5FF0"
    yellow_api_key: str = "yk_681b3ecc3cd97058726c7bd8552420410d9c25fae0e846cea3b7169ef3409398"

    model_config = {"env_file": Path(__file__).parent.parent.parent / ".env"}


settings = Settings()
