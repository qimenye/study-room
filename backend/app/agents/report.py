"""学习报告 Agent：本地统计 + 可选的大模型点评。"""

from typing import Optional

from sqlalchemy.orm import Session

from ..core.timeutil import to_local
from ..models import StudySession, User
from ..services import stats as stats_service
from .llm import LLMConfig, complete_detailed

SYSTEM_PROMPT = (
    "你是一位学习数据分析师。基于给定的统计数据写一份不超过 300 字的周报，"
    "内容包含：本周总体情况、值得肯定的地方、一条可执行的改进建议。不要编造数据。"
)


def _humanize(seconds: int) -> str:
    minutes = int(seconds) // 60
    if minutes < 60:
        return "%d 分钟" % minutes
    return "%d 小时 %d 分钟" % (minutes // 60, minutes % 60)


def build_local_report(db: Session, user: User) -> str:
    data = stats_service.summary(db, user)
    top_sessions = (
        db.query(StudySession)
        .filter(StudySession.user_id == user.id, StudySession.status == "finished")
        .order_by(StudySession.start_time.desc())
        .limit(5)
        .all()
    )

    lines = [
        "## %s 的学习报告" % user.nickname,
        "",
        "- 本周专注：" + _humanize(data["week_duration"]),
        "- 本月专注：" + _humanize(data["month_duration"]),
        "- 今日专注：" + _humanize(data["today_duration"]) + "（%d 次）" % data["today_count"],
        "- 累计专注：" + _humanize(data["total_duration"]),
        "- 连续打卡：%d 天" % data["streak_days"],
        "",
        "### 最近几次专注",
    ]
    if not top_sessions:
        lines.append("- 还没有完成的专注记录，先跑通一次 25 分钟番茄钟吧。")
    else:
        for session in top_sessions:
            local_time = to_local(session.start_time, user.timezone)
            lines.append(
                "- %s · %s · %d 分钟"
                % (
                    local_time.strftime("%m-%d %H:%M") if local_time else "-",
                    "番茄钟" if session.mode == "pomodoro" else "正计时",
                    int(session.duration or 0) // 60,
                )
            )

    lines += ["", "### 建议"]
    if data["week_duration"] < 3600 * 3:
        lines.append("- 本周总时长偏少，建议先把目标定在每天 1 个番茄钟，稳定比强度更重要。")
    elif data["streak_days"] >= 5:
        lines.append("- 打卡连续性很好，注意安排休息日，避免疲劳导致的断档。")
    else:
        lines.append("- 保持当前节奏，尽量固定在同一个时间段开始，习惯更容易养成。")
    return "\n".join(lines)


async def generate_report(
    db: Session, user: User, use_llm: bool = True, config: Optional[LLMConfig] = None
) -> tuple:
    """返回 (报告 Markdown, 来源, 兜底原因)。来源 llm=大模型，template=本地统计。"""
    local_report = build_local_report(db, user)
    if not use_llm:
        return local_report, "template", ""

    data = stats_service.summary(db, user)
    prompt = (
        "用户昵称：%(name)s\n今日时长：%(today)s 分钟\n本周时长：%(week)s 分钟\n"
        "本月时长：%(month)s 分钟\n累计时长：%(total)s 分钟\n连续打卡：%(streak)s 天\n"
        "今日专注次数：%(count)s 次\n最长单次：%(longest)s 分钟\n\n数据如下（Markdown）：\n%(report)s"
        % {
            "name": user.nickname,
            "today": data["today_duration"] // 60,
            "week": data["week_duration"] // 60,
            "month": data["month_duration"] // 60,
            "total": data["total_duration"] // 60,
            "streak": data["streak_days"],
            "count": data["today_count"],
            "longest": data["longest_duration"] // 60,
            "report": local_report,
        }
    )
    reply, error = await complete_detailed(
        SYSTEM_PROMPT, prompt, temperature=0.6, max_tokens=1600, config=config
    )
    if reply:
        return reply, "llm", ""
    return local_report, "template", error or "大模型没有返回内容"


def next_week_suggestion(db: Session, user: User) -> Optional[str]:
    data = stats_service.summary(db, user)
    if data["week_duration"] == 0:
        return "下周先设定一个最小目标：每天 25 分钟。"
    target_minutes = max(30, data["week_duration"] // 60 // 5 + 10)
    return "下周可以把单日目标设为 %d 分钟，比本周略高一点即可。" % target_minutes
