from typing import List, Optional

from pydantic import BaseModel, Field


class EncourageIn(BaseModel):
    room_id: Optional[int] = None
    scene: str = Field(default="start", pattern="^(start|during|finish)$")
    duration_minutes: int = Field(default=0, ge=0, le=1440)


class EncourageOut(BaseModel):
    message: str
    agent: str = "companion"
    source: str = "template"  # template / llm


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    room_id: Optional[int] = None


class ChatOut(BaseModel):
    reply: str
    source: str = "template"
    # 走了模板兜底时，这里是"为什么没连上大模型"的人话说明
    note: str = ""
    history: List[dict] = []


class PlanIn(BaseModel):
    goal: str = Field(min_length=1, max_length=200)
    weeks: int = Field(default=4, ge=1, le=52)
    hours_per_week: int = Field(default=10, ge=1, le=100)


class PlanOut(BaseModel):
    plan_id: int
    goal: str
    weeks: int
    content: str
    source: str = "template"
    note: str = ""
