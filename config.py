from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./agenteval.db"
    ANTHROPIC_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_STARTER: str = ""
    STRIPE_PRICE_ID_DEEP: str = ""
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    OPERATOR_EMAIL: str = ""
    OPERATOR_PASSWORD: str = ""
    BASE_URL: str = "http://localhost:8000"
    CALENDLY_URL: str = ""
    REPORT_DIR: str = "./reports"

    class Config:
        env_file = ".env"


settings = Settings()
