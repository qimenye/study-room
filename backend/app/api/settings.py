"""个性化设置：目前是 AI 模型配置（自带 API Key）。

Key 只写进后端数据库，接口只回掩码；前端永远拿不到明文。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents.llm import DEFAULT_BASE_URLS, PROVIDERS, PROVIDER_KEYS, LLMConfig, mask_key, probe
from ..config import settings
from ..core.deps import get_current_user
from ..core.ratelimit import hit
from ..database import get_db
from ..models import User
from ..schemas.llm import LLMSettingsIn
from ..schemas.music import MusicSettingsIn, MusicTestIn
from ..services import llm_settings, music_settings, netease

router = APIRouter(prefix="/api/settings", tags=["设置"])

DEFAULT_MODELS = {item["key"]: (item["models"][0] if item["models"] else "") for item in PROVIDERS}


def _form_defaults(row) -> dict:
    """表单回显：用户存过就用用户的，否则用服务端配置，再否则给个常见预设。"""
    if row is not None and row.llm_provider:
        provider = row.llm_provider
    elif settings.llm_enabled:
        provider = settings.llm_provider
    else:
        provider = "deepseek"

    base_url = (row.llm_base_url if row else "") or DEFAULT_BASE_URLS.get(provider, "")
    if not base_url and settings.llm_enabled:
        base_url = settings.llm_base_url

    model = (row.llm_model if row else "") or DEFAULT_MODELS.get(provider, "")
    if not model and settings.llm_enabled:
        model = settings.llm_model
    return {"provider": provider, "base_url": base_url, "model": model}


def _state(db: Session, current_user: User) -> dict:
    row = llm_settings.get_row(db, current_user.id)
    config, source = llm_settings.resolve(db, current_user)
    state = _form_defaults(row)
    state.update(
        {
            "has_key": bool(row and row.llm_api_key),
            "key_masked": mask_key(row.llm_api_key if row else ""),
            "source": source,  # user=用你自己的 Key / env=用服务端 .env / none=没配，走模板兜底
            "llm_ready": config.enabled,
            "effective_provider": config.provider if config.enabled else "",
            "effective_model": config.model if config.enabled else "",
            "env": {
                "configured": settings.llm_enabled,
                "provider": settings.llm_provider,
                "model": settings.llm_model,
            },
            "providers": PROVIDERS,
        }
    )
    return state


@router.get("/llm")
def read_llm_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return _state(db, current_user)


def _validate(payload: LLMSettingsIn) -> dict:
    provider = (payload.provider or "").strip().lower()
    if provider not in PROVIDER_KEYS:
        raise HTTPException(status_code=400, detail="不支持的 provider：%s" % provider)
    base_url = (payload.base_url or "").strip()
    if base_url and not base_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="接口地址必须以 http:// 或 https:// 开头")
    model = (payload.model or "").strip()
    if not model:
        raise HTTPException(status_code=400, detail="请填写模型名，例如 deepseek-chat")

    api_key = None
    if payload.api_key is not None:
        api_key = payload.api_key.strip()
        if api_key and len(api_key) < 8:
            raise HTTPException(status_code=400, detail="API Key 看起来不完整")
    return {"provider": provider, "base_url": base_url, "model": model, "api_key": api_key}


@router.put("/llm")
def update_llm_settings(
    payload: LLMSettingsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = _validate(payload)
    row = llm_settings.get_row(db, current_user.id)
    effective_key = data["api_key"] if data["api_key"] is not None else (row.llm_api_key if row else "")
    if not effective_key and data["provider"] != "ollama":
        raise HTTPException(status_code=400, detail="请填写 API Key（本地 Ollama 才不需要）")
    llm_settings.save(db, current_user, **data)
    return _state(db, current_user)


@router.delete("/llm")
def delete_llm_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    llm_settings.clear(db, current_user)
    return _state(db, current_user)


@router.post("/llm/test")
async def test_llm_settings(
    payload: Optional[LLMSettingsIn] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """用表单里的值（不落库）真实打一次接口，用来验证 Key 能用。"""
    if not hit("llm_test", current_user.id, limit=5):
        raise HTTPException(status_code=429, detail="测试太频繁了，等一分钟再试")

    row = llm_settings.get_row(db, current_user.id)
    form = _form_defaults(row)
    provider = ((payload.provider if payload else "") or form["provider"]).strip().lower()
    base_url = ((payload.base_url if payload else "") or form["base_url"]).strip()
    model = ((payload.model if payload else "") or form["model"]).strip()
    typed_key = (payload.api_key if payload and payload.api_key else "").strip()
    api_key = typed_key or (row.llm_api_key if row else "")

    if provider not in PROVIDER_KEYS:
        return {"ok": False, "message": "不支持的 provider"}

    config = LLMConfig(provider=provider, api_key=api_key, base_url=base_url, model=model)
    ok, message = await probe(config)
    return {"ok": ok, "message": message, "provider": provider, "model": model}


def _music_state(db: Session, current_user: User) -> dict:
    row = music_settings.get_row(db, current_user.id)
    cookie = row.netease_cookie if row else ""
    return {
        "has_cookie": bool(cookie),
        "cookie_masked": netease.mask_cookie(cookie),
        "nickname": row.netease_nickname if row else "",
        "source": "user" if cookie else "none",
    }


@router.get("/music")
def read_music_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return _music_state(db, current_user)


@router.put("/music")
def update_music_settings(
    payload: MusicSettingsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if payload.cookie is None:
        return _music_state(db, current_user)
    cookie = netease.normalize_cookie(payload.cookie)
    if not cookie:
        raise HTTPException(status_code=400, detail="请粘贴 MUSIC_U 或整段 Cookie")
    if not netease.cookie_usable(cookie):
        raise HTTPException(status_code=400, detail="Cookie 看起来不完整，MUSIC_U 至少要有 8 个字符")
    music_settings.save(db, current_user, cookie, nickname="")
    return _music_state(db, current_user)


@router.delete("/music")
def delete_music_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    music_settings.clear(db, current_user)
    return _music_state(db, current_user)


@router.post("/music/test")
async def test_music_settings(
    payload: Optional[MusicTestIn] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """真打一次网易云账户接口，验证 Cookie 是否还能用。"""
    if not hit("music_test", current_user.id, limit=6):
        raise HTTPException(status_code=429, detail="测试太频繁了，等一分钟再试")

    typed = netease.normalize_cookie(payload.cookie or "") if payload else ""
    cookie = typed or music_settings.get_cookie(db, current_user.id)
    if not cookie:
        return {"ok": False, "message": "还没填 Cookie"}
    ok, message, nickname = await netease.probe(cookie)
    if ok and not typed:
        music_settings.save(db, current_user, None, nickname=nickname or "网易云用户")
    return {"ok": ok, "message": message, "nickname": nickname}
