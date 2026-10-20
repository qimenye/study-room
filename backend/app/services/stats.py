"""统计聚合服务：学习记录、热力图、排行榜共用同一套口径。"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.timeutil import (
    day_range_utc,
    local_today,
    month_range_utc,
    to_local,
    utcnow,
    week_range_utc,
)
from ..models import StudySession, User

FINISHED = "finished"


def period_range(period: str, tz_name: Optional[str] = None) -> Optional[Tuple[datetime, datetime]]:
    """返回 UTC 区间；period=all 时返回 None 表示不限制。"""
    today = local_today(tz_name)
    if period == "today":
        return day_range_utc(today, tz_name)
    if period == "week":
        return week_range_utc(today, tz_name)
    if period == "month":
        return month_range_utc(today, tz_name)
    return None


def sum_duration(
    db: Session,
    user_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> int:
    query = db.query(func.coalesce(func.sum(StudySession.duration), 0)).filter(
        StudySession.user_id == user_id,
        StudySession.status == FINISHED,
    )
    if start is not None:
        query = query.filter(StudySession.start_time >= start)
    if end is not None:
        query = query.filter(StudySession.start_time < end)
    return int(query.scalar() or 0)


def summary(db: Session, user: User, tz_name: Optional[str] = None) -> Dict[str, int]:
    tz = tz_name or user.timezone
    today_range = period_range("today", tz)
    week_range = period_range("week", tz)
    month_range = period_range("month", tz)

    today_duration = sum_duration(db, user.id, *today_range) if today_range else 0
    week_duration = sum_duration(db, user.id, *week_range) if week_range else 0
    month_duration = sum_duration(db, user.id, *month_range) if month_range else 0

    base = db.query(StudySession).filter(
        StudySession.user_id == user.id, StudySession.status == FINISHED
    )
    total_duration = int(
        db.query(func.coalesce(func.sum(StudySession.duration), 0))
        .filter(StudySession.user_id == user.id, StudySession.status == FINISHED)
        .scalar()
        or 0
    )
    today_count = 0
    longest = 0
    if today_range:
        today_count = int(
            base.filter(
                StudySession.start_time >= today_range[0],
                StudySession.start_time < today_range[1],
            ).count()
        )
        longest = int(
            db.query(func.coalesce(func.max(StudySession.duration), 0))
            .filter(
                StudySession.user_id == user.id,
                StudySession.status == FINISHED,
                StudySession.start_time >= today_range[0],
                StudySession.start_time < today_range[1],
            )
            .scalar()
            or 0
        )
    else:
        today_count = int(base.count())
        longest = int(
            db.query(func.coalesce(func.max(StudySession.duration), 0))
            .filter(StudySession.user_id == user.id, StudySession.status == FINISHED)
            .scalar()
            or 0
        )

    return {
        "today_duration": today_duration,
        "week_duration": week_duration,
        "month_duration": month_duration,
        "total_duration": total_duration,
        "today_count": today_count,
        "longest_duration": longest,
        "streak_days": streak_days(db, user, tz),
    }


def streak_days(db: Session, user: User, tz_name: Optional[str] = None) -> int:
    """连续打卡天数（按用户本地日期计算）。"""
    tz = tz_name or user.timezone
    since = utcnow() - timedelta(days=400)
    rows = (
        db.query(StudySession.start_time)
        .filter(
            StudySession.user_id == user.id,
            StudySession.status == FINISHED,
            StudySession.duration > 0,
            StudySession.start_time >= since,
        )
        .all()
    )
    studied = {to_local(row[0], tz).date() for row in rows if row[0] is not None}
    if not studied:
        return 0

    today = local_today(tz)
    cursor: date = today if today in studied else today - timedelta(days=1)
    streak = 0
    while cursor in studied:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def heatmap(db: Session, user: User, days: int = 180, tz_name: Optional[str] = None) -> Dict:
    tz = tz_name or user.timezone
    days = max(1, min(days, 730))
    today = local_today(tz)
    start_day = today - timedelta(days=days - 1)
    start_utc = day_range_utc(start_day, tz)[0]
    end_utc = day_range_utc(today, tz)[1]

    rows = (
        db.query(StudySession.start_time, StudySession.duration)
        .filter(
            StudySession.user_id == user.id,
            StudySession.status == FINISHED,
            StudySession.start_time >= start_utc,
            StudySession.start_time < end_utc,
        )
        .all()
    )

    buckets: Dict[date, List[int]] = {}
    for start_time, duration in rows:
        if start_time is None:
            continue
        day = to_local(start_time, tz).date()
        bucket = buckets.setdefault(day, [0, 0])
        bucket[0] += int(duration or 0)
        bucket[1] += 1

    items: List[Dict] = []
    max_duration = 0
    cursor = start_day
    while cursor <= today:
        total, count = buckets.get(cursor, [0, 0])
        max_duration = max(max_duration, total)
        items.append({"date": cursor.isoformat(), "duration": total, "count": count})
        cursor += timedelta(days=1)

    return {"days": items, "max_duration": max_duration}


def ranking(db: Session, period: str = "today", tz_name: Optional[str] = None, limit: int = 50) -> List[Dict]:
    rng = period_range(period, tz_name)
    duration_expr = func.coalesce(func.sum(StudySession.duration), 0)
    count_expr = func.count(StudySession.id)

    query = (
        db.query(
            User.id.label("user_id"),
            User.nickname.label("nickname"),
            User.avatar.label("avatar"),
            duration_expr.label("duration"),
            count_expr.label("session_count"),
        )
        .join(StudySession, StudySession.user_id == User.id)
        .filter(StudySession.status == FINISHED, StudySession.duration > 0)
    )
    if rng:
        query = query.filter(StudySession.start_time >= rng[0], StudySession.start_time < rng[1])

    rows = (
        query.group_by(User.id)
        .order_by(duration_expr.desc(), User.id.asc())
        .limit(max(1, min(limit, 200)))
        .all()
    )

    items: List[Dict] = []
    for index, row in enumerate(rows, start=1):
        items.append(
            {
                "rank": index,
                "user_id": row.user_id,
                "nickname": row.nickname,
                "avatar": row.avatar or "",
                "duration": int(row.duration or 0),
                "session_count": int(row.session_count or 0),
            }
        )
    return items