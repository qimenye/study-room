"""房间氛围 Agent：欢迎新成员、按主题推荐白噪音、冷场提醒。"""

from typing import Tuple

# 房间主题 -> 推荐白噪音键（前端 Web Audio 合成，无需音频文件）
TOPIC_SOUND_MAP = {
    "考研": "library",
    "考试": "library",
    "编程": "cafe",
    "代码": "cafe",
    "写作": "rain",
    "阅读": "library",
    "冥想": "waves",
    "自习": "rain",
    "外语": "cafe",
    "默认": "rain",
}

SOUND_LABELS = {
    "rain": "雨声",
    "cafe": "咖啡馆",
    "library": "图书馆",
    "waves": "海浪",
    "brown": "布朗噪声",
}


def recommend_sound(topic: str) -> Tuple[str, str]:
    """根据房间主题推荐白噪音，返回 (键, 中文名)。"""
    for keyword, sound in TOPIC_SOUND_MAP.items():
        if keyword and keyword in (topic or ""):
            return sound, SOUND_LABELS.get(sound, sound)
    sound = TOPIC_SOUND_MAP["默认"]
    return sound, SOUND_LABELS.get(sound, sound)


def welcome_message(nickname: str, topic: str, sound_label: str) -> str:
    return "欢迎 %s 加入「%s」房间，试试%s，更容易进入状态。" % (nickname, topic or "自习", sound_label)


def idle_nudge(minutes_idle: int) -> str:
    if minutes_idle >= 30:
        return "房间安静了 %d 分钟，要不要一起开一轮番茄钟？" % minutes_idle
    return "休息够了就回来，开一轮 25 分钟。"