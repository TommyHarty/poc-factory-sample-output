import functools

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="FastAPI POC Starter", validation_alias="APP_NAME")
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
