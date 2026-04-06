from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Any
from pydantic import validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Suplementos Admin"
    APP_ROOT_PATH: str = ""
    CURRENCY_SYMBOL: str = "₡"
    COUNTRY_PHONE_CODE: str = "506"
    DEFAULT_TIMEZONE: str = "America/Costa_Rica"
    COMPANY_ICON_CLASS: str = "fa-solid fa-dumbbell"
    
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    DATABASE_URL: str
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: str | Any) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # WhatsApp - Strictly Required without defaults
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str
    WHATSAPP_VERIFY_TOKEN: str
    
    # n8n - Strictly Required without defaults
    N8N_WEBHOOK_URL: str
    N8N_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
