from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Skillnetic API"
    app_env: str = "local"
    app_debug: bool = True
    frontend_base_url: str = "http://localhost:3000"
    auth_state_secret: str = "skillnetic-auth-state-secret"
    session_cookie_name: str = "skillnetic_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    database_url: str = "postgresql+psycopg://aiskill:aiskill@localhost:5432/aiskill"
    redis_url: str = "redis://localhost:6379/0"
    resend_api_key: str = ""
    resend_from_email: str = "skillnetic.ai <onboarding@resend.dev>"
    resend_reply_to: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:8000/api/v1/auth/github/callback"
    github_api_token: str = ""
    test_auth_token: str = "ai-skill-test-token"
    test_auth_email: str = "submit-demo@aiskill.local"
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3100",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
