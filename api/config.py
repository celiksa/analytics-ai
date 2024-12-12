# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    # OpenAI settings
    openai_api_key: str
    
    # Database settings
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int = 54320
    
    # Model configuration
    model_name: str = "gpt-4o"
    
    @property
    def database_url_template(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}"
    
    def get_database_url(self, database_name: str) -> str:
        return f"{self.database_url_template}/{database_name}"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

@lru_cache
def get_settings() -> Settings:
    return Settings()