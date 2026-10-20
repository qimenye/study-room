"""学习计划 Agent：把大目标拆成周计划。"""

from typing import Dict, List, Optional, Tuple

from .llm import LLMConfig, complete_detailed

SYSTEM_PROMPT = (
    "你是一位学习规划师。把用户目标拆解成周计划，输出 Markdown："
    "每周包含【目标】【每日任务】【验收标准】三部分。要具体、可执行、可量化，不要空话。"
)


def build_local_plan(goal: str, weeks: int, hours_per_week: int) -> str:
    """本地模板拆解：按总时长均分，前松后紧。"""
    weeks = max(1, weeks)
    total_minutes = max(weeks * 1, hours_per_week * 60 * weeks)
    lines: List[str] = [
        "# 学习计划：%s" % goal,
        "",
        "- 周期：%d 周" % weeks,
        "- 每周投入：约 %d 小时" % hours_per_week,
        "- 总投入：约 %d 小时" % (total_minutes // 60),
        "",
        "## 总目标",
        "用 %d 周完成「%s」，每周都有可检查的产出。" % (weeks, goal),
        "",
    ]

    daily_minutes = max(20, (hours_per_week * 60) // 6)
    for week in range(1, weeks + 1):
        ratio = 0.7 + 0.6 * (week - 1) / max(1, weeks - 1) if weeks > 1 else 1.0
        week_minutes = int(daily_minutes * ratio)
        if week == 1:
            focus = "打基础并确认学习方法，把最薄弱的环节列出来"
            check = "能用自己的话复述基础概念，并完成一次自测"
        elif week == weeks:
            focus = "整体复盘与查漏补缺，做一次完整模拟"
            check = "模拟得分达到自定目标，错题全部订正"
        else:
            focus = "推进主线内容，按章节推进并同步整理笔记"
            check = "本周章节的练习题正确率不低于 80%"

        lines += [
            "## 第 %d 周" % week,
            "- 每日任务：%d 分钟专注，拆成 %d 个番茄钟" % (week_minutes, max(1, week_minutes // 25)),
            "- 本周重点：%s" % focus,
            "- 验收标准：%s" % check,
            "",
        ]

    lines += [
        "## 执行提醒",
        "- 每周日晚上花 10 分钟回顾：完成了多少、卡在哪里、下周怎么调整。",
        "- 单日未达标不要补时长，优先保证连续性和专注质量。",
    ]
    return "\n".join(lines)


async def generate_plan(
    goal: str,
    weeks: int,
    hours_per_week: int,
    config: Optional[LLMConfig] = None,
) -> Tuple[str, str, str]:
    fallback = build_local_plan(goal, weeks, hours_per_week)
    prompt = "目标：%s\n周期：%d 周\n每周可投入：%d 小时\n请输出周计划。" % (goal, weeks, hours_per_week)
    reply, error = await complete_detailed(
        SYSTEM_PROMPT, prompt, temperature=0.5, max_tokens=2400, config=config
    )
    if reply:
        return reply, "llm", ""
    return fallback, "template", error or "大模型没有返回内容"


def plan_progress_hint(weeks_done: int, weeks_total: int) -> Dict[str, str]:
    if weeks_total <= 0:
        weeks_total = 1
    percent = int(weeks_done * 100 / weeks_total)
    if percent >= 100:
        return {"percent": "100%", "hint": "计划周期已走完，建议做一次总复盘并制定新计划。"}
    if percent >= 50:
        return {"percent": "%d%%" % percent, "hint": "已经过半，重点转向查漏补缺。"}
    return {"percent": "%d%%" % percent, "hint": "前期重点是稳定执行，不要急着加量。"}
