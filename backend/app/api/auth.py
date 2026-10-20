from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.security import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas.user import TokenOut, UserCreate, UserLogin

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenOut:
    username = payload.username.strip().lower()
    exists = db.query(User).filter(User.username == username).first()
    if exists is not None:
        raise HTTPException(status_code=400, detail="用户名已被占用")

    nickname = (payload.nickname or payload.username).strip() or username
    user = User(
        username=username,
        nickname=nickname,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    username = payload.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        # 不区分"用户不存在"和"密码错误"，避免账号枚举
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    return TokenOut(access_token=create_access_token(user.id), user=user)