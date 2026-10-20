from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    topic: str = Field(default="自习", max_length=32)
    description: str = Field(default="", max_length=255)
    max_users: int = Field(default=12, ge=2, le=50)


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    topic: str
    description: str
    owner_id: Optional[int]
    max_users: int
    is_official: bool
    created_at: datetime

    # 由接口额外填充（来自内存中的实时状态）
    online_count: int = 0
    focusing_count: int = 0


class RoomMemberOut(BaseModel):
    user_id: int
    username: str
    nickname: str
    avatar: str
    status: str
    seat: Optional[int]
    online: bool = False


class RoomDetailOut(RoomOut):
    members: List[RoomMemberOut] = []