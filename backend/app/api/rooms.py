from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..core.timeutil import utcnow
from ..database import get_db
from ..models import Room, RoomMember, User
from ..schemas.room import RoomCreate, RoomDetailOut, RoomMemberOut, RoomOut
from ..websocket.room_manager import manager

router = APIRouter(prefix="/api/rooms", tags=["房间"])

RECENT_SECONDS = 120


def _live_stats(db: Session, room_id: int) -> dict:
    """优先用内存中的实时连接；为空时回退到数据库最近心跳。"""
    stats = manager.stats(room_id)
    if stats["online_count"] > 0:
        return stats

    recent = utcnow() - timedelta(seconds=RECENT_SECONDS)
    rows = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.status != "away", RoomMember.last_seen >= recent)
        .all()
    )
    return {
        "room_id": room_id,
        "online_count": len(rows),
        "focusing_count": sum(1 for row in rows if row.status == "focusing"),
        "resting_count": sum(1 for row in rows if row.status == "resting"),
    }


def _to_room_out(db: Session, room: Room) -> RoomOut:
    stats = _live_stats(db, room.id)
    data = RoomOut.model_validate(room)
    data.online_count = stats["online_count"]
    data.focusing_count = stats["focusing_count"]
    return data


@router.get("", response_model=List[RoomOut])
def list_rooms(
    topic: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RoomOut]:
    query = db.query(Room)
    if topic.strip():
        query = query.filter(Room.topic == topic.strip())
    rooms = query.order_by(Room.is_official.desc(), Room.id.asc()).all()
    return [_to_room_out(db, room) for room in rooms]


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomOut:
    room = Room(
        name=payload.name.strip(),
        topic=payload.topic.strip() or "自习",
        description=payload.description.strip(),
        owner_id=current_user.id,
        max_users=payload.max_users,
        is_official=False,
    )
    db.add(room)
    db.flush()  # 拿到 room.id 后再写入成员关系
    db.add(
        RoomMember(
            room_id=room.id,
            user_id=current_user.id,
            status="resting",
            last_seen=utcnow(),
        )
    )
    db.commit()
    db.refresh(room)
    return _to_room_out(db, room)


@router.get("/{room_id}", response_model=RoomDetailOut)
def room_detail(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomDetailOut:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在")

    base = _to_room_out(db, room)
    detail = RoomDetailOut.model_validate(room)
    detail.online_count = base.online_count
    detail.focusing_count = base.focusing_count

    online_ids = set(manager.online_user_ids(room_id))
    recent = utcnow() - timedelta(seconds=RECENT_SECONDS)
    rows = (
        db.query(RoomMember, User)
        .join(User, User.id == RoomMember.user_id)
        .filter(RoomMember.room_id == room_id)
        .all()
    )

    members: List[RoomMemberOut] = []
    for member, user in rows:
        is_online = user.id in online_ids or (member.last_seen and member.last_seen >= recent)
        if member.status == "away" and not is_online:
            continue
        members.append(
            RoomMemberOut(
                user_id=user.id,
                username=user.username,
                nickname=user.nickname,
                avatar=user.avatar or "",
                status=member.status,
                seat=member.seat,
                online=is_online,
            )
        )
    members.sort(key=lambda item: (item.seat is None, item.seat or 0))
    detail.members = members
    return detail


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在")
    if room.is_official:
        raise HTTPException(status_code=403, detail="官方房间不可删除")
    if room.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有房主可以删除房间")
    if manager.online_count(room_id) > 0:
        raise HTTPException(status_code=400, detail="房间内还有人在线，无法删除")

    db.query(RoomMember).filter(RoomMember.room_id == room_id).delete()
    db.delete(room)
    db.commit()


@router.post("/{room_id}/join", response_model=RoomOut)
def join_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoomOut:
    """HTTP 侧的入房（真正实时状态通过 WebSocket 建立）。"""
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在")

    online_ids = set(manager.online_user_ids(room_id))
    # WebSocket 可能还没建连，因此把"最近心跳过的成员"也算作占用座位，
    # 让"房间已满"尽早返回；强校验仍在 WebSocket connect 里。
    recent = utcnow() - timedelta(seconds=RECENT_SECONDS)
    recent_rows = (
        db.query(RoomMember.user_id)
        .filter(
            RoomMember.room_id == room_id,
            RoomMember.status != "away",
            RoomMember.last_seen >= recent,
        )
        .all()
    )
    occupied = online_ids | {row[0] for row in recent_rows}
    if current_user.id not in occupied and len(occupied) >= room.max_users:
        raise HTTPException(status_code=409, detail="房间人数已满")

    member = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == current_user.id)
        .first()
    )
    if member is None:
        db.add(RoomMember(room_id=room_id, user_id=current_user.id, status="resting"))
    else:
        member.last_seen = utcnow()
    db.commit()
    return _to_room_out(db, room)


@router.post("/{room_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    member = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == current_user.id)
        .first()
    )
    if member is not None:
        member.status = "away"
        member.seat = None
        member.last_seen = utcnow()
        db.commit()