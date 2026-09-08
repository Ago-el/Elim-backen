from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ELIM API"
    environment: str = "production"
    api_prefix: str = "/api/v1"
    database_url: str
    jwt_secret: str
    jwt_exp_minutes: int = 60
    admin_email: str = ""
    admin_password: str = ""
    cors_origins: str = "*"
    firebase_credentials_json: str = ""
    firebase_project_id: str = ""
    r2_endpoint: str = ""
    r2_bucket: str = "elim-media"
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_public_base_url: str = ""
    r2_presign_expiry_seconds: int = 900
    max_upload_size_mb: int = 512

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
