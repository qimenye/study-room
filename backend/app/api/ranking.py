from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models import User
from ..schemas.session import RankingItem
from ..services import stats as stats_service

router = APIRouter(prefix="/api/ranking", tags=["排行榜"])


@router.get("", response_model=List[RankingItem])
def read_ranking(
    period: str = Query(default="today", pattern="^(today|week|month|all)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RankingItem]:
    items = stats_service.ranking(db, period, current_user.timezone, limit)
    return [RankingItem(**item) for item in items]