from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SessionStart(BaseModel):
    room_id: Optional[int] = None
    mode: str = Field(default="pomodoro", pattern="^(pomodoro|countup)$")
    planned_minutes: int = Field(default=25, ge=1, le=600)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    room_id: Optional[int]
    mode: str
    planned_minutes: int
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    paused_total: int
    duration: int
    completed: bool


class SessionActiveOut(BaseModel):
    session: Optional[SessionOut] = None
    # 服务端当前时间（UTC），前端用它校正倒计时，避免设备时间不准
    server_time: datetime
    # 服务端算好的净专注秒数（已扣除暂停），前端直接用它恢复，避免自己推导出错
    elapsed_seconds: int = 0


class StatsOut(BaseModel):
    today_duration: int
    week_duration: int
    month_duration: int
    total_duration: int
    today_count: int
    longest_duration: int
    streak_days: int


class HeatmapDay(BaseModel):
    date: str
    duration: int
    count: int


class HeatmapOut(BaseModel):
    days: List[HeatmapDay]
    max_duration: int


class RankingItem(BaseModel):
    rank: int
    user_id: int
    nickname: str
    avatar: str
    duration: int
    session_count: int