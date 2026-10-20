from sqlalchemy import Boolean, Column, DateTime, Integer, String

from ..core.timeutil import utcnow
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(32), nullable=False)
    avatar = Column(String(255), nullable=False, default="")
    timezone = Column(String(64), nullable=False, default="Asia/Shanghai")
    total_duration = Column(Integer, nullable=False, default=0)  # 累计学习秒数（冗余字段，便于排行榜）
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)