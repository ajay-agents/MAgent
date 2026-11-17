from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_FERNET_KEY = "TCrC4ia8OmMdaOqI8B4-jsWcTQ_gmdf2artbFy5025g="  # dev only — never use in production
_DEV_JWT_SECRET = "dev-secret-change-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"  # development | production

    # AI providers — a provider is used only when its key is set
    openai_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    ai_timeout_seconds: float = 45.0
    # Return a canned email when every provider fails. Never enabled in production.
    ai_mock_fallback: bool = True

    fernet_key: str = _DEV_FERNET_KEY
    jwt_secret: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Google OAuth for sending through the Gmail API (optional — App Passwords work without it)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/mailbox/google/callback"
    frontend_url: str = "http://localhost:5173"  # where the OAuth callback sends the browser back to

    # Max emails one user sends per rolling 24 hours. Gmail allows ~500 (personal) / ~2,000 (Workspace);
    # staying under that avoids the account being temporarily blocked from sending.
    daily_send_limit: int = 400

    # Public base URL of this API, used in unsubscribe links inside sent emails
    public_api_url: str = "http://localhost:8000"

    # Shown on the upgrade screen until online payments are added
    support_email: str = ""

    database_url: str = "sqlite:///./mailflow.db"
    cors_origins: str = "http://localhost:5173"  # comma-separated
    log_level: str = "INFO"

    # Per-IP request limits (requests per minute)
    rate_limit_auth_per_minute: int = 10
    rate_limit_generate_per_minute: int = 20

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("openai_api_key", "gemini_api_key", "groq_api_key", "fernet_key", "jwt_secret",
                     "google_client_id", "google_client_secret", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("fernet_key")
    @classmethod
    def _valid_fernet_key(cls, v: str) -> str:
        try:
            Fernet(v.encode())
        except Exception:
            raise ValueError(
                "FERNET_KEY is not a valid Fernet key. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        return v

    @model_validator(mode="after")
    def _production_guards(self):
        if not self.is_production:
            return self
        problems = []
        if self.jwt_secret == _DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be set to a random string of at least 32 characters")
        if self.fernet_key == _DEV_FERNET_KEY:
            problems.append("FERNET_KEY must be set (the built-in dev key is public)")
        if self.google_oauth_enabled and not self.google_redirect_uri.startswith("https://"):
            problems.append("GOOGLE_REDIRECT_URI must use https in production")
        if not self.public_api_url.startswith("https://"):
            problems.append("PUBLIC_API_URL must be the https URL recipients use to reach this API (unsubscribe links)")
        if "*" in self.cors_origin_list:
            problems.append("CORS_ORIGINS must list explicit origins, not '*'")
        if problems:
            raise ValueError("Unsafe production config:\n  - " + "\n  - ".join(problems))
        self.ai_mock_fallback = False
        return self


settings = Settings()
