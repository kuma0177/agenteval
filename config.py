from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./agenteval.db"
    ANTHROPIC_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_STARTER: str = ""
    STRIPE_PRICE_ID_DEEP: str = ""
    STRIPE_PRICE_ID_GROWTH: str = ""
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    RESEND_FROM_NAME: str = "AgentEval"
    # Gmail SMTP (alternative to Resend — set these if RESEND_API_KEY is empty)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    OPERATOR_EMAIL: str = ""
    OPERATOR_PASSWORD: str = ""
    BASE_URL: str = "http://localhost:8000"
    CALENDLY_URL: str = ""
    CALENDLY_DEBRIEF_URL: str = ""
    REPORT_DIR: str = "./reports"
    SECRET_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
