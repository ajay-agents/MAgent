from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    database_url: str = "sqlite:///./mailflow.db"

    class Config:
        env_file = ".env"


settings = Settings()
