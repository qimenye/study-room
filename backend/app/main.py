"""应用入口：注册路由、WebSocket、CORS、心跳清理任务。"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import agent, auth, music, ranking, rooms, sessions, settings as settings_api, users
from .config import settings
from .core.timeutil import utcnow
from .database import SessionLocal, init_db
from .models import RoomMember
from .seed import seed_official_rooms
from .websocket import routes as ws_routes
from .websocket.room_manager import manager


async def _sweep_loop() -> None:
    """后台任务：清理心跳超时（直接关浏览器不发 close 帧）的连接。"""
    while True:
        await asyncio.sleep(settings.ws_sweep_interval)
        try:
            removed = await manager.sweep_stale(settings.ws_heartbeat_timeout)
            if not removed:
                continue
            db = SessionLocal()
            try:
                touched_rooms = set()
                for conn in removed:
                    touched_rooms.add(conn.room_id)
                    member = (
                        db.query(RoomMember)
                        .filter(
                            RoomMember.room_id == conn.room_id,
                            RoomMember.user_id == conn.user_id,
                        )
                        .first()
                    )
                    if member is not None:
                        member.status = "away"
                        member.seat = None
                        member.last_seen = utcnow()
                db.commit()
            finally:
                db.close()

            for room_id in touched_rooms:
                await manager.broadcast(
                    room_id,
                    {
                        "type": "room_state",
                        "members": manager.snapshot(room_id),
                        "stats": manager.stats(room_id),
                    },
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            # 清理任务绝不能把服务带崩
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_official_rooms()
    if settings.is_production and settings.jwt_secret_is_weak:
        raise RuntimeError("生产环境必须在 .env 里配置不少于 32 字节的随机 JWT_SECRET")

    task = asyncio.create_task(_sweep_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    description="线上虚拟自习室后端：认证 / 房间 / 专注记录 / 排行榜 / AI 智能体",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(rooms.router)
app.include_router(sessions.router)
app.include_router(ranking.router)
app.include_router(agent.router)
app.include_router(settings_api.router)
app.include_router(music.router)
app.include_router(ws_routes.router)


@app.get("/api/health", tags=["系统"])
def health() -> dict:
    return {
        "status": "ok",
        "version": settings.version,
        "server_time": utcnow().isoformat(),
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
        "llm_user_keys": True,  # 前端据此显示"可以在网页里配自己的 Key"
    }


# 可选：如果前端已经构建（frontend/dist），后端直接托管，单进程即可跑完整站点。
# 注意：这里是"预览用的静态托管"，前端改完要重新 npm run build 才会生效。
_dist = Path(settings.base_dir).parent / "frontend" / "dist"
if _dist.is_dir():
    _assets = _dist / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """前端用 history 路由，直接刷新 /rooms/3 这类地址时要回退到 index.html。"""
        if full_path.startswith(("api/", "ws/")) or full_path in {"docs", "redoc", "openapi.json"}:
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_dist / full_path).resolve() if full_path else None
        if candidate is not None and str(candidate).startswith(str(_dist)) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
