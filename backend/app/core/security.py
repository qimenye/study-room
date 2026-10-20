"""密码哈希与 JWT。"""

from datetime import timedelta
from typing import Any, Dict, Optional

import bcrypt
import jwt

from ..config import settings

_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    """bcrypt 只处理前 72 字节，这里统一截断，保证 hash/verify 行为一致。"""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, expires_minutes: Optional[int] = None) -> str:
    expire_minutes = expires_minutes or settings.access_token_expire_minutes
    from .timeutil import utcnow

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "iat": utcnow(),
        "exp": utcnow() + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[int]:
    """解析 token，返回 user_id；无效返回 None。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None