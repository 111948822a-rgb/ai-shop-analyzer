<<<<<<< HEAD
import os
=======
"""全局配置：从环境变量 / .env 读取，集中管理所有外部依赖。

v2 企业版新增：PostgreSQL、Redis、通义千问(Dashscope)、飞书、Celery。
开发期默认 SQLite，便于零依赖启动验收；生产在 .env 填 PostgreSQL 连接串即可，
SQLAlchemy 代码一行不用改。
"""
from functools import lru_cache
>>>>>>> f44a10f46c4881daf74503e50878a9fa023a8f16
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
<<<<<<< HEAD
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
=======
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 数据库：开发默认 SQLite；生产改成 postgresql+psycopg://user:pwd@host:5432/ai_shop
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    # 通义千问 / 阿里云 Dashscope
    dashscope_api_key: str = ""
    qwen_model: str = "qwen-max"

    # 飞书
    feishu_webhook_url: str = ""
    feishu_webhook_secret: str = ""            # 签名密钥（安全模式）
    feishu_event_verification_token: str = ""  # 事件订阅校验 token

    # 飞书开放平台（多维表格回写需要「应用身份」，与上面的自定义机器人不同）
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    # 飞书秒搭 Webhook 安全校验密钥（秒搭 -> AI 后端 的 X-Miaoda-Secret）
    miaoda_webhook_secret: str = ""

    # 飞书秒搭：是否用 Celery 跑异步分析。
    # False（默认）：Webhook 用 FastAPI BackgroundTasks 派发，已能防 HTTP 超时，零依赖。
    # True：改走 Celery（需 Redis + worker）。两者最终都调用 run_influencer_analysis。
    miaoda_use_celery: bool = False

    # 秒搭底层飞书多维表格（达人管理表）：app_token + 数据表 table_id
    miaoda_bitable_app_token: str = ""
    miaoda_bitable_table_id: str = ""

    # H5 报告页基址（用于拼 ai_report_url，秒搭 iframe 打开）
    frontend_base_url: str = "http://localhost:3000"

    # 文件
    upload_dir: str = "./uploads"
    max_upload_mb: int = 50

    # Celery（缺省复用 redis_url）
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
>>>>>>> f44a10f46c4881daf74503e50878a9fa023a8f16
