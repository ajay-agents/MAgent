from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    gemini_api_key: str = ""
    groq_api_key: str = ""
    fernet_key: str = "TCrC4ia8OmMdaOqI8B4-jsWcTQ_gmdf2artbFy5025g="  # dev default — replace in production
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    database_url: str = "sqlite:///./mailflow.db"

    class Config:
        env_file = ".env"


settings = Settings()
