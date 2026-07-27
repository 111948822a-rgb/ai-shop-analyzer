import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    MIAODA_SECRET: str = ""
    MIAODA_API_KEY: str = ""
    MIAODA_API_URL: str = ""
    DASHSCOPE_API_KEY: str = ""
    FEISHU_WEBHOOK_URL: str = ""
    FEISHU_SECRET: str = ""
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    REPORTS_BASE_URL: str = "http://localhost:3000"

    TK_PARTNER_APP_KEY: str = ""
    TK_PARTNER_APP_SECRET: str = ""
    TK_AUTH_SHOP_ID: str = ""
    TK_AUTH_ACCESS_TOKEN: str = ""
    TK_AUTH_REFRESH_TOKEN: str = ""
    TK_TOKEN_EXPIRES_AT: str = ""

    TK_APP_KEY: str = ""
    TK_APP_SECRET: str = ""
    TK_SHOP_ID: str = ""
    TK_ACCESS_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_type(self) -> str:
        if self.DATABASE_URL.startswith("postgresql"):
            return "postgresql"
        return "sqlite"

    @property
    def resolved_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(backend_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "db.sqlite3")
        return f"sqlite:///{db_path}"


settings = Settings()