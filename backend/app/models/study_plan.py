from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from ..core.timeutil import utcnow
from ..database import Base


class StudyPlan(Base):
    """学习计划：目标拆解成周计划，需要长期追踪，必须持久化。"""

    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal = Column(String(255), nullable=False)
    weeks = Column(Integer, nullable=False, default=4)
    content = Column(Text, nullable=False, default="")  # 结构化计划正文（Markdown）
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)