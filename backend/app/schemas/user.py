from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_\u4e00-\u9fa5]+$")
    password: str = Field(min_length=6, max_length=64)
    nickname: Optional[str] = Field(default=None, max_length=32)


class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=32)
    avatar: Optional[str] = Field(default=None, max_length=255)
    timezone: Optional[str] = Field(default=None, max_length=64)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    avatar: str
    timezone: str
    total_duration: int
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut