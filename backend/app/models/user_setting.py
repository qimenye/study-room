from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from ..core.timeutil import utcnow
from ..database import Base


class UserSetting(Base):
    """按用户存的个性化设置（目前只有 AI 模型配置）。

    API Key 只存在后端，接口只回掩码，明文永远不下发。
    """

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    llm_provider = Column(String(32), nullable=False, default="")
    llm_base_url = Column(String(255), nullable=False, default="")
    llm_model = Column(String(64), nullable=False, default="")
    llm_api_key = Column(String(255), nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
