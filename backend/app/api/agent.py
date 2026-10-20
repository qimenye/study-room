from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agents import companion, planner, report
from ..config import settings
from ..core.deps import get_current_user
from ..core.ratelimit import hit
from ..database import get_db
from ..models import AgentMessage, StudyPlan, User
from ..schemas.agent import (
    ChatIn,
    ChatOut,
    EncourageIn,
    EncourageOut,
    PlanIn,
    PlanOut,
)
from ..services import llm_settings

router = APIRouter(prefix="/api/agent", tags=["智能体"])

CHAT_SYSTEM_PROMPT = (
    "你是线上自习室的 AI 学习助手，负责答疑、拆解任务、陪用户专注。"
    "回答要简短（120 字以内）、具体、可执行，说人话，别用客套话和营销腔。"
    "用户顺带闲聊、问你是谁这类问题，一两句正常回应就行，不用刻意回避；"
    "只有明显与学习无关又需要长篇回答时，才礼貌地把话题拉回学习。"
)


def _guard(current_user: User) -> None:
    """限流：免费项目的 LLM 额度必须保护。"""
    if not hit("agent", current_user.id, limit=settings.agent_rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")


@router.post("/encourage", response_model=EncourageOut)
async def encourage(
    payload: EncourageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EncourageOut:
    _guard(current_user)
    config, _ = llm_settings.resolve(db, current_user)
    message, source = await companion.encourage(
        current_user.nickname, payload.scene, payload.duration_minutes, config=config
    )
    return EncourageOut(message=message, source=source)


@router.get("/report", response_model=dict)
async def read_report(
    use_llm: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _guard(current_user)
    config, _ = llm_settings.resolve(db, current_user)
    content, source, note = await report.generate_report(
        db, current_user, use_llm=use_llm, config=config
    )
    db.add(
        AgentMessage(
            user_id=current_user.id,
            agent="report",
            role="assistant",
            content=content,
        )
    )
    db.commit()
    return {
        "content": content,
        "source": source,
        "note": note,
        "suggestion": report.next_week_suggestion(db, current_user),
    }


@router.post("/plan", response_model=PlanOut)
async def create_plan(
    payload: PlanIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlanOut:
    _guard(current_user)
    config, _ = llm_settings.resolve(db, current_user)
    content, source, note = await planner.generate_plan(
        payload.goal, payload.weeks, payload.hours_per_week, config=config
    )

    plan = StudyPlan(
        user_id=current_user.id,
        goal=payload.goal.strip(),
        weeks=payload.weeks,
        content=content,
    )
    db.add(plan)
    db.add(
        AgentMessage(
            user_id=current_user.id,
            agent="planner",
            role="assistant",
            content="已生成学习计划：%s（%d 周）" % (payload.goal, payload.weeks),
        )
    )
    db.commit()
    db.refresh(plan)
    return PlanOut(
        plan_id=plan.id,
        goal=plan.goal,
        weeks=plan.weeks,
        content=plan.content,
        source=source,
        note=note,
    )


@router.get("/plans", response_model=List[dict])
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    plans = (
        db.query(StudyPlan)
        .filter(StudyPlan.user_id == current_user.id)
        .order_by(StudyPlan.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": plan.id,
            "goal": plan.goal,
            "weeks": plan.weeks,
            "content": plan.content,
            "created_at": plan.created_at.isoformat(),
        }
        for plan in plans
    ]


@router.post("/chat", response_model=ChatOut)
async def chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatOut:
    _guard(current_user)

    history = (
        db.query(AgentMessage)
        .filter(AgentMessage.user_id == current_user.id, AgentMessage.agent == "companion")
        .order_by(AgentMessage.created_at.desc())
        .limit(6)
        .all()
    )
    history.reverse()
    context = "\n".join(
        ("用户：" if item.role == "user" else "助手：") + item.content for item in history
    )

    db.add(
        AgentMessage(
            user_id=current_user.id,
            room_id=payload.room_id,
            agent="companion",
            role="user",
            content=payload.message,
        )
    )
    db.commit()

    from ..agents.llm import complete_detailed

    config, _ = llm_settings.resolve(db, current_user)
    prompt = (context + "\n用户：" + payload.message).strip()
    reply, llm_error = await complete_detailed(
        CHAT_SYSTEM_PROMPT, prompt, temperature=0.7, max_tokens=700, config=config
    )
    note = ""
    if reply:
        source = "llm"
    else:
        source = "template"
        note = llm_error or "大模型没有返回内容"
        reply = companion.fallback_reply(payload.message, note)

    db.add(
        AgentMessage(
            user_id=current_user.id,
            room_id=payload.room_id,
            agent="companion",
            role="assistant",
            content=reply,
        )
    )
    db.commit()

    return ChatOut(
        reply=reply,
        source=source,
        note=note,
        history=[
            {"role": item.role, "content": item.content, "created_at": item.created_at.isoformat()}
            for item in history
        ],
    )
