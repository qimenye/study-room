from typing import Optional

from pydantic import BaseModel, Field


class MusicSettingsIn(BaseModel):
    # None = 不动已存的 Cookie；空串 = 清除
    cookie: Optional[str] = Field(default=None, max_length=8000)


class MusicTestIn(BaseModel):
    # 不传就用已保存的那份，方便"先测试再保存"
    cookie: Optional[str] = Field(default=None, max_length=8000)


class MusicCaptchaIn(BaseModel):
    phone: str = Field(..., max_length=20)
    country_code: str = Field(default="86", max_length=6)


class MusicPhoneLoginIn(MusicCaptchaIn):
    captcha: str = Field(..., max_length=8)
