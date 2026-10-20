from sqlalchemy import Boolean, Column, DateTime, Integer, String

from ..core.timeutil import utcnow
from ..database import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    topic = Column(String(32), nullable=False, default="自习")
    description = Column(String(255), nullable=False, default="")
    owner_id = Column(Integer, nullable=True)  # 官方房间无房主
    max_users = Column(Integer, nullable=False, default=12)
    is_official = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)