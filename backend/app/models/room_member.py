from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..core.timeutil import utcnow
from ..database import Base


class RoomMember(Base):
    """房间成员。status 会落库，用于服务重启后恢复"谁应该还在房间"。"""

    __tablename__ = "room_members"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_room_member"),)

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="resting")  # focusing / resting / away
    seat = Column(Integer, nullable=True)
    last_seen = Column(DateTime, nullable=False, default=utcnow)
    joined_at = Column(DateTime, nullable=False, default=utcnow)

    room = relationship("Room")
    user = relationship("User")