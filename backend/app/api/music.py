"""网易云搜索、扫码/验证码登录与音频代理。"""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, user_from_query_or_bearer
from ..core.ratelimit import hit
from ..database import get_db
from ..models import User
from ..schemas.music import MusicCaptchaIn, MusicPhoneLoginIn
from ..services import music_settings, netease

router = APIRouter(prefix="/api/music", tags=["音乐"])


def _cookie(db: Session, user: User) -> str:
    return music_settings.get_cookie(db, user.id)


def _phone(value: str, country_code: str) -> tuple:
    digits = re.sub(r"\D", "", value or "")
    country = re.sub(r"\D", "", country_code or "86") or "86"
    if len(country) > 4:
        raise HTTPException(status_code=400, detail="国家区号不对")
    if country == "86":
        # 用户经常把 +86 一起粘进手机号输入框，这里兼容一下
        if digits.startswith("0086"):
            digits = digits[4:]
        elif digits.startswith("86") and len(digits) == 13:
            digits = digits[2:]
        if not re.fullmatch(r"1\d{10}", digits):
            raise HTTPException(status_code=400, detail="中国大陆手机号是 11 位，以 1 开头")
    elif not 6 <= len(digits) <= 15:
        raise HTTPException(status_code=400, detail="手机号格式不对")
    return digits, country


def _captcha(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not 4 <= len(digits) <= 8:
        raise HTTPException(status_code=400, detail="验证码格式不对")
    return digits


@router.post("/login/qr")
async def create_qr_login(current_user: User = Depends(get_current_user)) -> dict:
    if not hit("music_qr_create", current_user.id, limit=12):
        raise HTTPException(status_code=429, detail="二维码生成得太频繁了，等一会儿再试")
    try:
        return await netease.qr_create()
    except netease.NeteaseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/login/qr/status")
async def qr_login_status(
    key: str = Query(..., min_length=8, max_length=80),
    session: str = Query(default="", max_length=4000),
    nmtid: str = Query(default="", max_length=4000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not hit("music_qr_poll", current_user.id, limit=120):
        raise HTTPException(status_code=429, detail="轮询太快了，稍等两秒")
    try:
        # nmtid 是旧前端使用的参数名，保留兼容，避免缓存里的旧页面扫码后卡住。
        result = await netease.qr_status(key, session or nmtid)
    except netease.NeteaseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result.get("status") != "confirmed":
        return result

    cookie = result.pop("cookie", "")
    # 昵称只是锦上添花；账户接口偶尔抽风时仍然保存 Cookie，不影响播放。
    _, _, nickname = await netease.probe(cookie)
    music_settings.save(db, current_user, cookie, nickname=nickname or "网易云用户")
    return {"status": "confirmed", "message": "登录成功", "nickname": nickname}


@router.post("/login/captcha")
async def send_login_captcha(
    payload: MusicCaptchaIn,
    current_user: User = Depends(get_current_user),
) -> dict:
    if not hit("music_captcha", current_user.id, limit=3, window_seconds=600):
        raise HTTPException(status_code=429, detail="验证码发得太频繁了，10 分钟后再试")
    phone, country = _phone(payload.phone, payload.country_code)
    try:
        return await netease.send_captcha(phone, country, str(current_user.id))
    except netease.NeteaseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login/phone")
async def phone_login(
    payload: MusicPhoneLoginIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not hit("music_phone_login", current_user.id, limit=10):
        raise HTTPException(status_code=429, detail="登录尝试太频繁了，等一分钟再试")
    phone, country = _phone(payload.phone, payload.country_code)
    captcha = _captcha(payload.captcha)
    try:
        result = await netease.phone_login(phone, captcha, country, str(current_user.id))
    except netease.NeteaseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    nickname = result.get("nickname") or ""
    if not nickname:
        _, _, probed = await netease.probe(result["cookie"])
        nickname = probed
    music_settings.save(
        db, current_user, result["cookie"], nickname=nickname or "网易云用户"
    )
    return {"ok": True, "message": "登录成功", "nickname": nickname}


@router.get("/search")
async def search_music(
    q: str = Query(..., min_length=1, max_length=60),
    limit: int = Query(default=20, ge=1, le=30),
    offset: int = Query(default=0, ge=0, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(user_from_query_or_bearer),
) -> dict:
    if not hit("music_search", current_user.id, limit=40):
        raise HTTPException(status_code=429, detail="搜得太快了，歇一分钟再试")
    try:
        return await netease.search(q, _cookie(db, current_user), limit=limit, offset=offset)
    except netease.NeteaseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/stream/{song_id}")
async def stream_song(
    song_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_from_query_or_bearer),
) -> StreamingResponse:
    """把网易云 CDN 的音频同源转发给 <audio>，并透传 Range 支持拖动进度。"""
    if song_id <= 0:
        raise HTTPException(status_code=400, detail="歌曲 ID 不对")
    try:
        client, response = await netease.open_stream(
            song_id, _cookie(db, current_user), request.headers.get("range")
        )
    except netease.NeteaseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    async def body():
        try:
            async for chunk in response.aiter_raw():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    headers = {}
    for key in (
        "content-length",
        "content-range",
        "accept-ranges",
        "content-type",
        "content-encoding",
        "etag",
        "last-modified",
    ):
        value = response.headers.get(key)
        if value:
            headers[key] = value
    headers.setdefault("accept-ranges", "bytes")
    headers["cache-control"] = "no-store"
    return StreamingResponse(body(), status_code=response.status_code, headers=headers)
