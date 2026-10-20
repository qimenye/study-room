"""网易云登录态的读写。

Cookie 只存后端；对外只给掩码，和 AI Key 的处理方式保持一致。
"""

from typing import Optional

from sqlalchemy.orm import Session

from ..models import MusicSetting, User


def get_row(db: Session, user_id: int) -> Optional[MusicSetting]:
    return db.query(MusicSetting).filter(MusicSetting.user_id == user_id).first()


def get_cookie(db: Session, user_id: int) -> str:
    row = get_row(db, user_id)
    return row.netease_cookie if row else ""


def save(
    db: Session, user: User, cookie: Optional[str], nickname: Optional[str] = None
) -> MusicSetting:
    """cookie / nickname 传 None 表示保持原样。"""
    row = get_row(db, user.id)
    if row is None:
        row = MusicSetting(user_id=user.id, netease_cookie="")
        db.add(row)
    if cookie is not None:
        row.netease_cookie = cookie
    if nickname is not None:
        row.netease_nickname = nickname
    db.commit()
    db.refresh(row)
    return row


def clear(db: Session, user: User) -> None:
    row = get_row(db, user.id)
    if row is not None:
        db.delete(row)
        db.commit()
