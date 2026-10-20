"""学习陪伴 Agent：进入房间打招呼、专注中鼓励、结束总结。"""

import random
from typing import Optional, Tuple

from .llm import LLMConfig, complete

SYSTEM_PROMPT = (
    "你是线上自习室里的学习陪伴助手，语气温和、简短、具体，不说空话。"
    "回复控制在 60 字以内，不要使用 emoji 堆砌，不要营销腔。"
)

TEMPLATES = {
    "start": [
        "{name}，开始啦。先把这一次的目标想清楚，剩下的交给计时器。",
        "欢迎回来，{name}。专注的时候不用追求完美，先动起来最重要。",
        "{name} 上线了，这一轮我们只做一件事：把手头这个任务推进一点点。",
    ],
    "during": [
        "已经专注 {minutes} 分钟了，保持住这个节奏。",
        "{minutes} 分钟了，呼吸一下，继续。",
        "状态不错，{minutes} 分钟专注已经过去了，别急着看手机。",
    ],
    "finish": [
        "这一轮 {minutes} 分钟完成了，记录已经存好。休息一下再继续。",
        "{minutes} 分钟专注结束，记得起身活动两分钟。",
        "完成 {minutes} 分钟专注，今天又攒下一段了。",
    ],
}


def template_message(scene: str, nickname: str, duration_minutes: int) -> str:
    options = TEMPLATES.get(scene, TEMPLATES["start"])
    return random.choice(options).format(name=nickname, minutes=duration_minutes)


def fallback_reply(question: str, reason: str) -> str:
    """大模型没答上来的兜底回复：说清原因 + 给一条能立刻用的建议。

    早期版本这里直接甩一句"欢迎回来"式的问候，问什么都答同一句，看起来就像
    "答非所问"；现在改成如实说明 + 通用方法，至少不误导。
    """
    return (
        "这次没连上大模型，下面是本地兜底回复。\n"
        "原因：" + (reason or "接口没有返回内容") + "\n\n"
        "可以先到「模型设置」点一次「测试连接」，确认 Key 和模型名。"
        "在修好之前，先给你一条通用的：把要学的内容切成一个 25 分钟能做完的小块，"
        "从最容易开始的那一步动手，做完再决定下一步。"
    )


async def encourage(
    nickname: str,
    scene: str = "start",
    duration_minutes: int = 0,
    config: Optional[LLMConfig] = None,
) -> Tuple[str, str]:
    """返回 (文案, 来源)。来源为 template 表示走了兜底。"""
    fallback = template_message(scene, nickname, duration_minutes)
    scene_hint = {
        "start": "用户刚进入自习室，准备开始专注。",
        "during": "用户正在专注中，已经坚持了 %d 分钟。" % duration_minutes,
        "finish": "用户刚完成一轮 %d 分钟的专注。" % duration_minutes,
    }.get(scene, "用户正在使用自习室。")

    reply = await complete(
        SYSTEM_PROMPT,
        "场景：%s\n用户昵称：%s\n请给一句陪伴式的话。" % (scene_hint, nickname),
        temperature=0.9,
        max_tokens=400,
        config=config,
    )
    if reply:
        return reply, "llm"
    return fallback, "template"


def completion_summary(duration_minutes: int, planned_minutes: int) -> str:
    """结束时的本地总结（不调用 LLM，保证即时返回）。"""
    if planned_minutes and duration_minutes >= planned_minutes:
        return "本轮计划 %d 分钟，实际专注 %d 分钟，按计划完成。" % (planned_minutes, duration_minutes)
    if duration_minutes <= 0:
        return "本轮没有产生有效专注时长，下次挑一个更小的目标试试。"
    return "本轮计划 %d 分钟，实际专注 %d 分钟，中途有中断也正常。" % (planned_minutes, duration_minutes)
