from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings - the brain of the app

       Why BaseSettings?
       - Automatic environment variable loading
       - Type validation (prevents string where int expected)
       - Default values with fallbacks
    """
    #DB configurations
    DATABASE_URl:str = "postgresql://user:password@localhost/news_intelligence"

    #api keys
    NEWS_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    #application settings
    APP_NAME:str = 'News System '
    DEBUG: bool= True #enable detail msg in development

    #api config
    API_PREFIX = "/api"

    class config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
