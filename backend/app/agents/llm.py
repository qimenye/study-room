"""LLM 调用封装：只依赖 OpenAI 兼容协议，失败时返回 None 让上层走模板兜底。

Key 有两个来源：
1. 服务端 `.env`（全局默认，给"懒得配"的场景兜底）；
2. 用户在网页「AI 助手 → 模型设置」里自己填的（存数据库，按用户隔离）。

安全约定：API Key 只停留在后端，接口只返回掩码，明文绝不下发。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..config import settings

# 常见模型都提供 OpenAI 兼容端点；前端"模型设置"面板直接读这张表渲染预设
PROVIDERS: List[Dict[str, Any]] = [
    {
        "key": "deepseek",
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "need_key": True,
        "note": "便宜、有免费额度，最推荐",
    },
    {
        "key": "qwen",
        "label": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-turbo"],
        "need_key": True,
        "note": "阿里云百炼，注册送额度",
    },
    {
        "key": "glm",
        "label": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-flash", "glm-4-air"],
        "need_key": True,
        "note": "glm-4-flash 有免费档",
    },
    {
        "key": "openai",
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "need_key": True,
        "note": "需要能访问外网",
    },
    {
        "key": "ollama",
        "label": "本地 Ollama",
        "base_url": "http://127.0.0.1:11434/v1",
        "models": ["qwen2.5:7b", "llama3.1:8b"],
        "need_key": False,
        "note": "完全免费、不用 Key，但要先在本机跑起来",
    },
    {
        "key": "custom",
        "label": "自定义（OpenAI 兼容）",
        "base_url": "",
        "models": [],
        "need_key": True,
        "note": "任何兼容 /chat/completions 的端点",
    },
]

PROVIDER_KEYS = {item["key"] for item in PROVIDERS}
DEFAULT_BASE_URLS = {item["key"]: item["base_url"] for item in PROVIDERS if item["base_url"]}


@dataclass
class LLMConfig:
    """一份可用的模型配置（服务端或用户级都归一成它）。"""

    provider: str = "mock"
    api_key: str = ""
    base_url: str = ""
    model: str = ""

    @property
    def needs_key(self) -> bool:
        return self.provider != "ollama"

    @property
    def enabled(self) -> bool:
        """provider 是 mock/none，或者缺 Key、缺地址时都视为不可用。"""
        if self.provider in {"", "mock", "none"}:
            return False
        if self.needs_key and not self.api_key:
            return False
        return bool(self.base_url or DEFAULT_BASE_URLS.get(self.provider))

    @property
    def endpoint(self) -> Optional[str]:
        if not self.enabled:
            return None
        base = self.base_url or DEFAULT_BASE_URLS.get(self.provider, "")
        if not base:
            return None
        return base.rstrip("/") + "/chat/completions"

    def headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.needs_key:
            headers["Authorization"] = "Bearer " + self.api_key
        return headers


def env_config() -> LLMConfig:
    """服务端 .env 里的那份配置。"""
    return LLMConfig(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
    )


def mask_key(key: str) -> str:
    """只露头尾，用来告诉前端"已经存过 Key 了"。"""
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "***"
    return key[:5] + "***" + key[-4:]


# 推理型模型（deepseek-reasoner / *-flash 之类）会先吐一大段思考，
# 思考也算 max_tokens，正文还没开始就被截断了，所以留一份更大的重试额度
RETRY_MIN_TOKENS = 2048
RETRY_MAX_TOKENS = 8000

HTTP_HINTS = {
    400: "（模型名或请求参数不对）",
    401: "（API Key 不对或没有权限）",
    403: "（API Key 没有权限）",
    404: "（接口地址或模型名不对）",
    429: "（被限流或额度用完了）",
}


def _http_error(response: "httpx.Response") -> str:
    hint = HTTP_HINTS.get(response.status_code, "")
    snippet = " ".join((response.text or "").split())[:160]
    return "HTTP %d%s %s" % (response.status_code, hint, snippet)


async def _chat(
    cfg: LLMConfig,
    url: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> Tuple[Optional[str], Optional[str], str]:
    """打一次 /chat/completions。

    返回 (正文, 思考内容, 错误说明)：三者只会有一个"有值"，出错时正文和思考都是 None。
    """
    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=cfg.headers())
    except Exception as exc:
        return None, None, "连不上 %s：%s（检查网络或接口地址）" % (
            cfg.provider,
            exc.__class__.__name__,
        )

    if response.status_code >= 400:
        return None, None, _http_error(response)

    try:
        data = response.json()
    except Exception:
        return None, None, "接口返回的不是 JSON（HTTP %d）" % response.status_code

    choices = data.get("choices") or []
    if not choices:
        return None, None, "接口没有返回 choices：" + str(data)[:120]

    message = (choices[0].get("message") or {})
    content = (message.get("content") or "").strip()
    # deepseek-reasoner 等推理模型把过程放在 reasoning_content 里
    reasoning = (message.get("reasoning_content") or message.get("reasoning") or "").strip()
    if content:
        return content, None, ""
    if reasoning:
        return None, reasoning, ""
    return None, None, "模型返回了空内容（finish_reason=%s）" % (
        choices[0].get("finish_reason") or "?"
    )


async def complete_detailed(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
    config: Optional[LLMConfig] = None,
) -> Tuple[Optional[str], str]:
    """调用大模型，返回 (正文, 失败原因)。成功时失败原因是空串。"""
    cfg = config or env_config()
    url = cfg.endpoint
    if url is None:
        missing = "API Key" if cfg.needs_key and not cfg.api_key else "接口地址"
        return None, "没有可用的模型配置：还缺" + missing

    text, reasoning, error = await _chat(
        cfg, url, system_prompt, user_prompt, temperature, max_tokens, 30.0
    )
    if text:
        return text, ""
    if error:
        return None, error

    # 只拿到思考内容 → 大概率是推理模型把额度用完了，加额度重试一次
    bigger = min(RETRY_MAX_TOKENS, max(max_tokens * 8, RETRY_MIN_TOKENS))
    text, reasoning, error = await _chat(
        cfg, url, system_prompt, user_prompt, temperature, bigger, 60.0
    )
    if text:
        return text, ""
    if error:
        return None, error
    return None, (
        "「%s」是推理模型，只输出了思考过程没有正文；换成 deepseek-chat 这类对话模型最稳"
        % cfg.model
    )


async def complete(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
    config: Optional[LLMConfig] = None,
) -> Optional[str]:
    """调用大模型；不可用或出错时返回 None（上层走模板兜底）。"""
    text, _ = await complete_detailed(system_prompt, user_prompt, temperature, max_tokens, config)
    return text


async def probe(config: LLMConfig) -> Tuple[bool, str]:
    """真实打一次接口，给"测试连接"按钮用；返回 (是否成功, 人话说明)。"""
    url = config.endpoint
    if url is None:
        missing = "API Key" if config.needs_key and not config.api_key else "接口地址"
        return False, "配置不完整：还缺" + missing

    text, reasoning, error = await _chat(
        config, url, "你是连通性测试助手，只按要求最短回复。", "只回复两个字：收到", 0, 512, 30.0
    )
    if error:
        return False, error
    if text:
        return True, "连接成功，%s 可用" % config.model
    if reasoning:
        return True, (
            "能连上，但 %s 是推理模型：它先输出思考、正文被额度截断了。"
            "建议把模型改成 deepseek-chat" % config.model
        )
    return False, "能连上，但模型没有返回内容，检查一下模型名"
