from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..core.timeutil import utcnow
from ..database import get_db
from ..models import StudySession, User
from ..schemas.session import (
    HeatmapOut,
    SessionActiveOut,
    SessionOut,
    SessionStart,
    StatsOut,
)
from ..services import stats as stats_service

router = APIRouter(prefix="/api/sessions", tags=["专注记录"])

ACTIVE_STATUSES = ("running", "paused")
STALE_HOURS = 12


def _own_session(db: Session, session_id: int, user: User) -> StudySession:
    session = db.get(StudySession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="专注记录不存在")
    return session


def _cancel_stale(db: Session, user: User) -> None:
    """清理异常退出（关机/崩溃）留下的僵尸会话，避免时长被无限累计。"""
    from datetime import timedelta

    cutoff = utcnow() - timedelta(hours=STALE_HOURS)
    stale = (
        db.query(StudySession)
        .filter(
            StudySession.user_id == user.id,
            StudySession.status.in_(ACTIVE_STATUSES),
            StudySession.start_time < cutoff,
        )
        .all()
    )
    if not stale:
        return
    for session in stale:
        session.status = "cancelled"
        session.end_time = utcnow()
        session.paused_at = None
        session.duration = 0
    db.commit()


def _net_duration(session: StudySession, now) -> int:
    """服务端口径的净学习时长：暂停时间不计入。前端传来的秒数一律不采信。"""
    elapsed = int((now - session.start_time).total_seconds())
    paused = int(session.paused_total or 0)
    if session.status == "paused" and session.paused_at is not None:
        paused += int((now - session.paused_at).total_seconds())
    return max(0, elapsed - paused)


@router.post("/start", response_model=SessionOut)
def start_session(
    payload: SessionStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudySession:
    _cancel_stale(db, current_user)

    active = (
        db.query(StudySession)
        .filter(StudySession.user_id == current_user.id, StudySession.status.in_(ACTIVE_STATUSES))
        .first()
    )
    if active is not None:
        raise HTTPException(status_code=409, detail="已有进行中的专注会话，请先结束")

    session = StudySession(
        user_id=current_user.id,
        room_id=payload.room_id,
        mode=payload.mode,
        planned_minutes=payload.planned_minutes,
        status="running",
        start_time=utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/pause", response_model=SessionOut)
def pause_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudySession:
    session = _own_session(db, session_id, current_user)
    if session.status == "paused":
        return session
    if session.status != "running":
        raise HTTPException(status_code=400, detail="会话已结束")

    session.status = "paused"
    session.paused_at = utcnow()
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/resume", response_model=SessionOut)
def resume_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudySession:
    session = _own_session(db, session_id, current_user)
    if session.status == "running":
        return session
    if session.status != "paused":
        raise HTTPException(status_code=400, detail="会话已结束")

    now = utcnow()
    if session.paused_at is not None:
        session.paused_total = int(session.paused_total or 0) + int(
            (now - session.paused_at).total_seconds()
        )
    session.paused_at = None
    session.status = "running"
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/end", response_model=SessionOut)
def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudySession:
    session = _own_session(db, session_id, current_user)
    if session.status in ("finished", "cancelled"):
        return session

    now = utcnow()
    duration = _net_duration(session, now)
    if session.status == "paused" and session.paused_at is not None:
        session.paused_total = int(session.paused_total or 0) + int(
            (now - session.paused_at).total_seconds()
        )

    session.paused_at = None
    session.end_time = now
    session.duration = duration
    session.status = "finished"
    session.completed = bool(
        session.mode == "pomodoro" and duration >= int(session.planned_minutes or 0) * 60
    )
    current_user.total_duration = int(current_user.total_duration or 0) + duration
    db.commit()
    db.refresh(session)
    return session


@router.get("/active", response_model=SessionActiveOut)
def active_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionActiveOut:
    """前端刷新/断线重连后调用，用服务端时间校正本地倒计时。"""
    _cancel_stale(db, current_user)
    session = (
        db.query(StudySession)
        .filter(StudySession.user_id == current_user.id, StudySession.status.in_(ACTIVE_STATUSES))
        .order_by(StudySession.start_time.desc())
        .first()
    )
    out: Optional[SessionOut] = SessionOut.model_validate(session) if session is not None else None
    elapsed = _net_duration(session, utcnow()) if session is not None else 0
    return SessionActiveOut(session=out, server_time=utcnow(), elapsed_seconds=elapsed)


@router.get("/records", response_model=List[SessionOut])
def list_records(
    period: str = Query(default="week", pattern="^(today|week|month|all)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[StudySession]:
    query = db.query(StudySession).filter(
        StudySession.user_id == current_user.id,
        StudySession.status == "finished",
    )
    rng = stats_service.period_range(period, current_user.timezone)
    if rng:
        query = query.filter(StudySession.start_time >= rng[0], StudySession.start_time < rng[1])
    return query.order_by(StudySession.start_time.desc()).limit(limit).all()


@router.get("/stats", response_model=StatsOut)
def read_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StatsOut:
    return StatsOut(**stats_service.summary(db, current_user))


@router.get("/heatmap", response_model=HeatmapOut)
def read_heatmap(
    days: int = Query(default=180, ge=7, le=730),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HeatmapOut:
    return HeatmapOut(**stats_service.heatmap(db, current_user, days))