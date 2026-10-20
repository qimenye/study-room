"""数据库连接与建表。"""

from typing import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    # FastAPI 在线程池里使用同一个 SQLite 连接，必须关掉线程检查
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """SQLite 默认不校验外键，这里显式打开。"""
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入用的数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表。生产环境建议换成 Alembic 迁移。"""
    from . import models  # noqa: F401  确保所有模型都已注册

    Base.metadata.create_all(bind=engine)
    _ensure_music_columns()


def _ensure_music_columns() -> None:
    """给早期版本的 music_settings 补字段。

    create_all 只会建新表，不会给已存在的表加列；这里做一次轻量迁移，
    避免用户升级后因为缺 netease_nickname 直接报错。
    """
    inspector = inspect(engine)
    if "music_settings" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("music_settings")}
    if "netease_nickname" in columns:
        return
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE music_settings ADD COLUMN netease_nickname VARCHAR(64) NOT NULL DEFAULT ''")
        )
