"""房间连接管理（进程内）。

设计要点：
1. 每个连接带 conn_id，重连时旧连接的 finally 不会误删新连接（真实竞态）；
2. last_seen + 后台清理任务处理"用户直接关浏览器、不发 close 帧"的情况；
3. 上量后这里换成 Redis Pub/Sub，接口保持不变。
"""

import asyncio
import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import WebSocket

from ..core.timeutil import utcnow

STATUSES = {"focusing", "resting", "away"}
_conn_seq = itertools.count(1)


@dataclass
class ClientConn:
    ws: WebSocket
    conn_id: int
    user_id: int
    username: str
    nickname: str
    avatar: str
    seat: int
    room_id: int = 0
    status: str = "resting"
    joined_at: datetime = field(default_factory=utcnow)
    last_seen: datetime = field(default_factory=utcnow)

    def public(self, online: bool = True) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "status": self.status,
            "seat": self.seat,
            "online": online,
        }

    def is_stale(self, timeout_seconds: int) -> bool:
        return (utcnow() - self.last_seen).total_seconds() > timeout_seconds


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: Dict[int, Dict[int, ClientConn]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        room_id: int,
        ws: WebSocket,
        user,
        max_users: int,
    ) -> Optional[ClientConn]:
        """加入房间；房间已满返回 None。若该用户已在房间，旧的连接会被关闭替换。"""
        stale_ws: Optional[WebSocket] = None
        async with self._lock:
            members = self._rooms.setdefault(room_id, {})
            existing = members.get(user.id)
            if existing is None and len(members) >= max_users:
                return None

            if existing is not None:
                stale_ws = existing.ws
                seat = existing.seat
            else:
                seat = self._next_seat(members, max_users)

            conn = ClientConn(
                ws=ws,
                conn_id=next(_conn_seq),
                user_id=user.id,
                username=user.username,
                nickname=user.nickname,
                avatar=user.avatar or "",
                seat=seat,
                room_id=room_id,
            )
            members[user.id] = conn

        if stale_ws is not None:
            try:
                await stale_ws.close(code=4409)  # 同一账号在新标签页重连
            except Exception:
                pass
        return conn

    @staticmethod
    def _next_seat(members: Dict[int, ClientConn], max_users: int) -> int:
        used = {conn.seat for conn in members.values()}
        for index in range(max_users):
            if index not in used:
                return index
        return len(members)

    async def disconnect(self, room_id: int, user_id: int, conn_id: int) -> bool:
        """返回 True 表示确实移除了连接。"""
        async with self._lock:
            members = self._rooms.get(room_id)
            if not members:
                return False
            current = members.get(user_id)
            if current is None or current.conn_id != conn_id:
                return False  # 已被新连接替换，不能误删
            members.pop(user_id, None)
            if not members:
                self._rooms.pop(room_id, None)
            return True

    async def set_status(self, room_id: int, user_id: int, status: str) -> bool:
        if status not in STATUSES:
            return False
        async with self._lock:
            conn = self._rooms.get(room_id, {}).get(user_id)
            if conn is None:
                return False
            conn.status = status
            return True

    async def touch(self, room_id: int, user_id: int) -> None:
        async with self._lock:
            conn = self._rooms.get(room_id, {}).get(user_id)
            if conn is not None:
                conn.last_seen = utcnow()

    def online_user_ids(self, room_id: int) -> List[int]:
        return list(self._rooms.get(room_id, {}).keys())

    def online_count(self, room_id: int) -> int:
        return len(self._rooms.get(room_id, {}))

    def focusing_count(self, room_id: int) -> int:
        return sum(1 for conn in self._rooms.get(room_id, {}).values() if conn.status == "focusing")

    def snapshot(self, room_id: int) -> List[dict]:
        members = list(self._rooms.get(room_id, {}).values())
        members.sort(key=lambda item: item.seat)
        return [conn.public(online=True) for conn in members]

    def stats(self, room_id: int) -> dict:
        members = list(self._rooms.get(room_id, {}).values())
        return {
            "room_id": room_id,
            "online_count": len(members),
            "focusing_count": sum(1 for conn in members if conn.status == "focusing"),
            "resting_count": sum(1 for conn in members if conn.status == "resting"),
        }

    def seats_taken(self, room_id: int) -> List[int]:
        return sorted(conn.seat for conn in self._rooms.get(room_id, {}).values())

    async def broadcast(self, room_id: int, message: dict, exclude_user_id: Optional[int] = None) -> None:
        targets = [
            conn
            for conn in list(self._rooms.get(room_id, {}).values())
            if exclude_user_id is None or conn.user_id != exclude_user_id
        ]
        if not targets:
            return
        await asyncio.gather(
            *[self._safe_send(conn.ws, message) for conn in targets],
            return_exceptions=True,
        )

    @staticmethod
    async def _safe_send(ws: WebSocket, message: dict) -> None:
        try:
            await ws.send_json(message)
        except Exception:
            pass

    async def sweep_stale(self, timeout_seconds: int) -> List[ClientConn]:
        """清理超时连接，返回被清理的连接列表（供上层更新数据库）。"""
        removed: List[ClientConn] = []
        async with self._lock:
            for room_id in list(self._rooms.keys()):
                members = self._rooms[room_id]
                for user_id in list(members.keys()):
                    conn = members[user_id]
                    if conn.is_stale(timeout_seconds):
                        removed.append(conn)
                        members.pop(user_id, None)
                if not members:
                    self._rooms.pop(room_id, None)

        for conn in removed:
            try:
                await conn.ws.close(code=4408)
            except Exception:
                pass
        return removed

    def reset(self) -> None:
        """测试用。"""
        self._rooms.clear()


manager = ConnectionManager()