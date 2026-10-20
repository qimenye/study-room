"""把"服务端 .env 配置"和"用户自己填的 Key"合成一份可用的 LLMConfig。

优先级：用户级 > 环境变量。用户级配了但没 Key（且不是 ollama）时视为没配，
这样"存了半截配置"不会把服务端的默认配置顶掉。
"""

from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..agents.llm import LLMConfig, env_config
from ..models import User, UserSetting


def get_row(db: Session, user_id: int) -> Optional[UserSetting]:
    return db.query(UserSetting).filter(UserSetting.user_id == user_id).first()


def _row_active(row: Optional[UserSetting]) -> bool:
    if row is None or not row.llm_provider:
        return False
    # 本地 Ollama 不需要 Key，其它 provider 必须有 Key 才算"配好了"
    return True if row.llm_provider == "ollama" else bool(row.llm_api_key)


def resolve(db: Session, user: User) -> Tuple[LLMConfig, str]:
    """返回 (配置, 来源)，来源取值为 user / env / none。"""
    row = get_row(db, user.id)
    if _row_active(row):
        return (
            LLMConfig(
                provider=row.llm_provider,
                api_key=row.llm_api_key,
                base_url=row.llm_base_url,
                model=row.llm_model,
            ),
            "user",
        )
    env = env_config()
    if env.enabled:
        return env, "env"
    return LLMConfig(provider="mock"), "none"


def save(
    db: Session,
    user: User,
    *,
    provider: str,
    base_url: str,
    model: str,
    api_key: Optional[str] = None,
) -> UserSetting:
    """api_key 传 None 表示"保持原样"，传空串表示"清掉"。"""
    row = get_row(db, user.id)
    if row is None:
        row = UserSetting(user_id=user.id)
        db.add(row)
    row.llm_provider = provider
    row.llm_base_url = base_url or ""
    row.llm_model = model or ""
    if api_key is not None:
        row.llm_api_key = api_key
    db.commit()
    db.refresh(row)
    return row


def clear(db: Session, user: User) -> None:
    """删掉用户级配置，回落到服务端 .env。"""
    row = get_row(db, user.id)
    if row is not None:
        db.delete(row)
        db.commit()
