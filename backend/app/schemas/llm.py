from typing import Optional

from pydantic import BaseModel, Field


class LLMSettingsIn(BaseModel):
    provider: str = Field(default="deepseek", max_length=32)
    base_url: str = Field(default="", max_length=255)
    model: str = Field(default="", max_length=64)
    # None = 不动已存的 Key；"" = 清除；其它 = 覆盖
    api_key: Optional[str] = Field(default=None, max_length=255)
