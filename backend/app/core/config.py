from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Agent Studio"
    debug: bool = False

    # Database
    database_url: str = Field(default="postgresql+asyncpg://agent:agent@localhost:5432/agent_studio")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Object Storage (MinIO)
    s3_endpoint: str = Field(default="http://localhost:9000")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="agent-studio")

    # Kubernetes
    k8s_config_path: str = Field(default="~/.kube/config")
    k8s_namespace_prefix: str = Field(default="agent-studio")

    # MLflow
    mlflow_tracking_uri: str = Field(default="http://localhost:5000")

    # lakeFS
    lakefs_endpoint: str = Field(default="http://localhost:8000")
    lakefs_access_key: str = Field(default="minioadmin")
    lakefs_secret_key: str = Field(default="minioadmin")

    # Auth
    secret_key: str = Field(default="change-me-in-production")
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # CORS
    cors_origins: list[str] = ["*"]


settings = Settings()
