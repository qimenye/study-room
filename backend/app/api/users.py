from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models import User
from ..schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    if data.get("nickname"):
        current_user.nickname = data["nickname"].strip()
    if data.get("avatar") is not None:
        current_user.avatar = data["avatar"]
    if data.get("timezone"):
        current_user.timezone = data["timezone"]
    db.commit()
    db.refresh(current_user)
    return current_user