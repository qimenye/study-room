from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from ..core.timeutil import utcnow
from ..database import Base


class MusicSetting(Base):
    """按用户存的网易云登录态（MUSIC_U Cookie）。

    Cookie 只存在后端，接口只回掩码；前端永远拿不到明文。
    """

    __tablename__ = "music_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    netease_cookie = Column(Text, nullable=False, default="")
    netease_nickname = Column(String(64), nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
