"""时间工具：数据库统一存 UTC 朴素时间，展示层按用户本地时区换算。

这是本项目最容易出错的地方之一：
- 存储层：naive UTC（不带 tzinfo），SQLite/PostgreSQL 行为一致；
- 计算层："今日/本周"必须先换算到用户本地时区，再转回 UTC 区间做查询。
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None  # type: ignore

_CHINA_TZ = timezone(timedelta(hours=8))


def utcnow() -> datetime:
    """当前 UTC 时间（朴素，无 tzinfo），用于所有入库字段。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_tz(name: Optional[str] = None):
    """获取时区对象；Windows 上缺少 tzdata 时退化为 UTC+8。"""
    tz_name = name or "Asia/Shanghai"
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    if tz_name in {"Asia/Shanghai", "Asia/Chongqing", "Asia/Harbin"}:
        return _CHINA_TZ
    return timezone.utc


def to_local(dt: Optional[datetime], tz_name: Optional[str] = None) -> Optional[datetime]:
    """UTC 朴素时间 -> 带时区的本地时间。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_tz(tz_name))


def local_range_to_utc(
    start_local: datetime, end_local: datetime, tz_name: Optional[str] = None
) -> Tuple[datetime, datetime]:
    """本地时间区间 -> UTC 朴素时间区间（左闭右开）。"""
    tz = get_tz(tz_name)
    if start_local.tzinfo is None:
        start_local = start_local.replace(tzinfo=tz)
    if end_local.tzinfo is None:
        end_local = end_local.replace(tzinfo=tz)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def day_range_utc(day: date, tz_name: Optional[str] = None) -> Tuple[datetime, datetime]:
    """某个本地自然日对应的 UTC 区间。"""
    start_local = datetime.combine(day, time.min)
    return local_range_to_utc(start_local, start_local + timedelta(days=1), tz_name)


def week_range_utc(day: date, tz_name: Optional[str] = None) -> Tuple[datetime, datetime]:
    """某个本地自然日所在周（周一为一周之始）对应的 UTC 区间。"""
    monday = day - timedelta(days=day.weekday())
    start_local = datetime.combine(monday, time.min)
    return local_range_to_utc(start_local, start_local + timedelta(days=7), tz_name)


def month_range_utc(day: date, tz_name: Optional[str] = None) -> Tuple[datetime, datetime]:
    """某个本地自然日所在月对应的 UTC 区间。"""
    first = day.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    return local_range_to_utc(
        datetime.combine(first, time.min),
        datetime.combine(next_first, time.min),
        tz_name,
    )


def local_today(tz_name: Optional[str] = None) -> date:
    return datetime.now(get_tz(tz_name)).date()


def local_day_keys_between(start: date, end: date, tz_name: Optional[str] = None) -> List[date]:
    """生成 [start, end] 之间的所有日期。"""
    days: List[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days