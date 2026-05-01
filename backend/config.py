from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./printfarm.db"
    GOVEE_API_KEY: Optional[str] = None
    AMAZON_EMAIL: Optional[str] = None
    AMAZON_PASSWORD: Optional[str] = None
    SLICER_WATCH_DIR: str = "/home/pi/slicer-output"
    ENERGY_RATE_PER_KWH: float = 0.12
    SECRET_KEY: str = "changeme"

    model_config = {"env_file": ".env"}


settings = Settings()
