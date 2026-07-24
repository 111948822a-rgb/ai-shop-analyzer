from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalize_db_url(url: str) -> str:
    """把连接串规范化为 SQLAlchemy 可接受的形式。

    - Render / 部分平台给出的 Postgres URL 以 ``postgres://`` 开头，
      SQLAlchemy 1.4+ 只认 ``postgresql://``，需替换。
    - Render 托管 Postgres 强制要求 SSL，若 URL 中未声明 ``sslmode`` 则补上
      ``?sslmode=require``（External Database URL 已自带，这里做兜底）。
    - 本地开发若 DATABASE_URL 缺失，保持默认 SQLite 不变。
    """
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    if url.startswith("postgresql://") and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    return url


database_url = _normalize_db_url(settings.database_url)

# SQLite 需关闭同线程检查（FastAPI 多线程访问）；Postgres 不需要。
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

# Postgres 建议加 pool_recycle（Render 会回收空闲连接），SQLite 不需要。
engine_kwargs: dict = {"pool_pre_ping": True}
if database_url.startswith("postgresql"):
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_size"] = 10

engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
