"""依赖注入：当前登录用户。"""

from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _load_user(db: Session, token: Optional[str]) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或凭证缺失")
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证无效或已过期")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else None
    return _load_user(db, token)


def user_from_ws_token(token: Optional[str] = Query(default=None), db: Session = Depends(get_db)) -> User:
    """WebSocket 无法自定义请求头，因此 token 走 query 参数。"""
    return _load_user(db, token)


def user_from_query_or_bearer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    """<audio src="..."> 带不了 Authorization 头，允许把 token 放在 query 里。"""
    return _load_user(db, credentials.credentials if credentials else token)
