"""房间 WebSocket 端点。

协议（客户端 -> 服务端）：
  {"type": "ping"}
  {"type": "status", "status": "focusing|resting|away"}
  {"type": "timer", "payload": {...}}          # 计时状态广播（服务端只转发，不信任时长）
  {"type": "chat", "content": "..."}           # 房间文字交流

协议（服务端 -> 客户端）：
  {"type": "room_state", "members": [...], "stats": {...}}
  {"type": "member_joined", "member": {...}}
  {"type": "member_left", "user_id": 1}
  {"type": "status_change", "user_id": 1, "status": "focusing"}
  {"type": "timer", "user_id": 1, "payload": {...}}
  {"type": "chat", "user_id": 1, "nickname": "...", "content": "..."}
  {"type": "pong", "server_time": "..."}
  {"type": "agent", "content": "..."}
  {"type": "error", "code": "...", "message": "..."}
"""

import json
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..agents import host
from ..core.ratelimit import hit
from ..core.security import decode_token
from ..core.timeutil import utcnow
from ..database import SessionLocal
from ..models import AgentMessage, Room, RoomMember, User
from .room_manager import STATUSES, manager

router = APIRouter()

CLOSE_UNAUTHORIZED = 4401
CLOSE_NOT_FOUND = 4404
CLOSE_FORBIDDEN = 4403
CLOSE_REPLACED = 4409
CLOSE_TIMEOUT = 4408


def _upsert_member(db: Session, room_id: int, user_id: int, seat: int, status: str) -> None:
    member = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
        .first()
    )
    if member is None:
        member = RoomMember(room_id=room_id, user_id=user_id, seat=seat, status=status, joined_at=utcnow())
        db.add(member)
    else:
        member.seat = seat
        member.status = status
        member.last_seen = utcnow()
    db.commit()


def _mark_member_away(room_id: int, user_id: int) -> None:
    db = SessionLocal()
    try:
        member = (
            db.query(RoomMember)
            .filter(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
            .first()
        )
        if member is not None:
            member.status = "away"
            member.seat = None
            member.last_seen = utcnow()
            db.commit()
    finally:
        db.close()


def _save_agent_line(room_id: int, user_id: int, content: str) -> None:
    db = SessionLocal()
    try:
        db.add(
            AgentMessage(
                user_id=user_id,
                room_id=room_id,
                agent="host",
                role="assistant",
                content=content,
            )
        )
        db.commit()
    finally:
        db.close()


@router.websocket("/ws/room/{room_id}")
async def room_socket(websocket: WebSocket, room_id: int, token: Optional[str] = Query(default=None)) -> None:
    await websocket.accept()

    user_id = decode_token(token) if token else None
    if user_id is None:
        await websocket.send_json({"type": "error", "code": "unauthorized", "message": "登录状态无效"})
        await websocket.close(code=CLOSE_UNAUTHORIZED)
        return

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        room = db.get(Room, room_id)
    finally:
        db.close()

    if user is None or room is None:
        await websocket.send_json({"type": "error", "code": "not_found", "message": "房间不存在"})
        await websocket.close(code=CLOSE_NOT_FOUND)
        return

    conn = await manager.connect(room_id, websocket, user, room.max_users)
    if conn is None:
        await websocket.send_json({"type": "error", "code": "room_full", "message": "房间人数已满"})
        await websocket.close(code=CLOSE_FORBIDDEN)
        return


    db = SessionLocal()
    try:
        _upsert_member(db, room_id, user.id, conn.seat, conn.status)
    finally:
        db.close()

    sound_key, sound_label = host.recommend_sound(room.topic)
    await manager.broadcast(
        room_id,
        {"type": "member_joined", "member": conn.public(online=True), "stats": manager.stats(room_id)},
        exclude_user_id=user.id,
    )
    await websocket.send_json(
        {
            "type": "room_state",
            "members": manager.snapshot(room_id),
            "stats": manager.stats(room_id),
            "self": conn.public(online=True),
            "welcome": {
                "message": host.welcome_message(user.nickname, room.topic, sound_label),
                "sound": sound_key,
                "sound_label": sound_label,
            },
        }
    )
    await manager.broadcast(
        room_id,
        {"type": "room_state", "members": manager.snapshot(room_id), "stats": manager.stats(room_id)},
        exclude_user_id=user.id,
    )

    try:
        while True:
            raw = await websocket.receive_text()
            await manager.touch(room_id, user.id)

            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                await websocket.send_json({"type": "error", "code": "bad_json", "message": "消息格式错误"})
                continue
            if not isinstance(data, dict):
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "server_time": utcnow().isoformat()})
                continue

            if msg_type == "status":
                status = str(data.get("status", ""))
                if not await manager.set_status(room_id, user.id, status):
                    await websocket.send_json(
                        {"type": "error", "code": "bad_status", "message": "状态值不合法"}
                    )
                    continue
                db = SessionLocal()
                try:
                    _upsert_member(db, room_id, user.id, conn.seat, status)
                finally:
                    db.close()
                await manager.broadcast(
                    room_id,
                    {
                        "type": "status_change",
                        "user_id": user.id,
                        "status": status,
                        "stats": manager.stats(room_id),
                    },
                )
                continue

            if msg_type == "timer":
                payload = data.get("payload") or {}
                if not isinstance(payload, dict):
                    payload = {}
                await manager.broadcast(
                    room_id,
                    {"type": "timer", "user_id": user.id, "payload": payload},
                )
                continue

            if msg_type == "chat":
                content = str(data.get("content", "")).strip()[:300]
                if not content:
                    continue
                if not hit("ws_chat", user.id, limit=20):
                    await websocket.send_json(
                        {"type": "error", "code": "rate_limited", "message": "发言太快，稍后再试"}
                    )
                    continue
                await manager.broadcast(
                    room_id,
                    {
                        "type": "chat",
                        "user_id": user.id,
                        "nickname": user.nickname,
                        "content": content,
                    },
                )
                continue

            await websocket.send_json({"type": "error", "code": "unknown_type", "message": "未知消息类型"})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        removed = await manager.disconnect(room_id, user.id, conn.conn_id)
        _mark_member_away(room_id, user.id)
        if removed:
            await manager.broadcast(
                room_id,
                {
                    "type": "member_left",
                    "user_id": user.id,
                    "stats": manager.stats(room_id),
                    "members": manager.snapshot(room_id),
                },
            )