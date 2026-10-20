"""内置官方常驻房间：解决"新用户进来发现所有房间都是空的"的冷启动问题。"""

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Room

OFFICIAL_ROOMS = [
    {
        "name": "静音自习室",
        "topic": "自习",
        "description": "全程静音，只需打开计时器",
        "max_users": 20,
    },
    {
        "name": "考研冲刺营",
        "topic": "考研",
        "description": "长期备考，互相监督进度",
        "max_users": 16,
    },
    {
        "name": "编程自习室",
        "topic": "编程",
        "description": "写代码、刷题、做项目",
        "max_users": 12,
    },
    {
        "name": "早读打卡间",
        "topic": "阅读",
        "description": "清晨共读，适合需要外力督促的你",
        "max_users": 12,
    },
]


def seed_official_rooms(db: Session = None) -> int:
    """返回新建的房间数（已存在时返回 0）。"""
    own_session = db is None
    session = db or SessionLocal()
    try:
        existing = session.query(Room).filter(Room.is_official.is_(True)).count()
        if existing > 0:
            return 0
        for item in OFFICIAL_ROOMS:
            session.add(Room(is_official=True, owner_id=None, **item))
        session.commit()
        return len(OFFICIAL_ROOMS)
    finally:
        if own_session:
            session.close()