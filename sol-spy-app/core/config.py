from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn


class RunConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080


class ApiPrefix(BaseModel):
    prefix: str = "/api"

class DatabaseConfig(BaseModel):
    url: PostgresDsn
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 50
    max_overflow: int = 10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("env","env.template"),
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",

    )
    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()
    db: DatabaseConfig


settings = Settings()
print(settings.db.url)