from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ..core.timeutil import utcnow
from ..database import Base


class StudySession(Base):
    """一次专注会话。

    时长口径：暂停时间不计入。
    duration = (end_time - start_time) - paused_total - 未结算的本次暂停
    """

    __tablename__ = "study_sessions"
    __table_args__ = (
        Index("ix_sessions_user_start", "user_id", "start_time"),
        Index("ix_sessions_start", "start_time"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    mode = Column(String(16), nullable=False, default="pomodoro")  # pomodoro / countup
    planned_minutes = Column(Integer, nullable=False, default=25)
    status = Column(String(16), nullable=False, default="running")  # running / paused / finished / cancelled

    start_time = Column(DateTime, nullable=False, default=utcnow)
    end_time = Column(DateTime, nullable=True)
    paused_total = Column(Integer, nullable=False, default=0)  # 累计暂停秒数
    paused_at = Column(DateTime, nullable=True)  # 本次暂停开始时间
    duration = Column(Integer, nullable=False, default=0)  # 最终净学习秒数
    completed = Column(Boolean, nullable=False, default=False)  # 番茄钟是否走满
    created_at = Column(DateTime, nullable=False, default=utcnow)

    user = relationship("User")
    room = relationship("Room")