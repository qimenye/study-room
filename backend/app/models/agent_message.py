from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from ..core.timeutil import utcnow
from ..database import Base


class AgentMessage(Base):
    """智能体对话与产出。学习计划/周报属于长期内容，必须落库（不能只放 Redis）。"""

    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    agent = Column(String(32), nullable=False, default="companion")  # companion / report / planner / host
    role = Column(String(16), nullable=False, default="assistant")  # user / assistant
    content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)