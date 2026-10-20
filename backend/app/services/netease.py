"""网易云音乐网页端的轻量代理。

浏览器不能直连网易云：一是没有公开的 CORS，二是跨域音频会污染 Web Audio，
AnalyserNode 拿不到数据，也就没法做可视化。所以统一由后端同源转发：
搜索、取播放地址、代理音频流（支持 Range，拖动进度条不用整首重下）。

这里用的是网易云网页端自己在用的接口，属于非官方用法，接口可能变化。
登录支持扫码和手机验证码，成功后把 MUSIC_U 等 Cookie 存到当前用户名下；
VIP / 版权受限的歌曲就靠这个登录态。
"""

import base64
import io
import json
import re
import secrets
import string
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx
import qrcode
import qrcode.image.svg
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

SEARCH_URL = "https://music.163.com/api/cloudsearch/pc"
PLAYER_URL = "https://music.163.com/api/song/enhance/player/url"
ACCOUNT_URL = "https://music.163.com/api/nuser/account/get"
QR_UNIKEY_URL = "https://music.163.com/weapi/login/qrcode/unikey"
QR_POLL_URL = "https://music.163.com/weapi/login/qrcode/client/login"
SMS_URL = "https://music.163.com/weapi/sms/captcha/sent"
PHONE_LOGIN_URL = "https://music.163.com/weapi/login/cellphone"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REFERER = "https://music.163.com/"

_MUSIC_U = re.compile(r"MUSIC_U=([^;]+)")
_CSRF = re.compile(r"__csrf=([^;]+)")

# 手机验证码是"先发码、再登录"两步，网易云会看同一个会话。
# 单人本地服务用内存存一下，进程重启后重新获取验证码即可。
_PHONE_SESSIONS: Dict[str, Dict[str, Any]] = {}
_PHONE_SESSION_TTL = 15 * 60

# 网易云 weapi 使用的固定参数（网页端公开在 JS 里）
_WEB_IV = b"0102030405060708"
_WEB_PRESET_KEY = b"0CoJUm6Qyw8W8jud"
_WEB_PUBLIC_KEY = "010001"
_WEB_MODULUS = (
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b"
    "3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda9"
    "2557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4"
    "875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7"
)
_WEB_CHARS = string.ascii_letters + string.digits


class NeteaseError(Exception):
    """带中文提示的代理错误，API 层直接转成 4xx/5xx。"""


def normalize_cookie(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    text = re.sub(r"[\r\n]+", " ", text)
    if "MUSIC_U" not in text:
        text = "MUSIC_U=" + text
    return text.strip(" ;")


def cookie_value(cookie: str) -> str:
    match = _MUSIC_U.search(cookie or "")
    return match.group(1).strip() if match else ""


def csrf_from_cookie(cookie: str) -> str:
    match = _CSRF.search(cookie or "")
    return match.group(1).strip() if match else ""


def cookie_usable(cookie: str) -> bool:
    return len(cookie_value(cookie)) >= 8


def mask_cookie(cookie: str) -> str:
    value = cookie_value(cookie)
    if not value:
        return ""
    return "MUSIC_U=****" + value[-4:]


def _headers(cookie: str = "") -> Dict[str, str]:
    headers = {
        "User-Agent": UA,
        "Referer": REFERER,
        "Origin": "https://music.163.com",
        "Accept": "application/json, text/plain, */*",
    }
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _aes_base64(text: bytes, key: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, _WEB_IV)
    return base64.b64encode(cipher.encrypt(pad(text, 16))).decode("ascii")


def weapi_payload(payload: Dict[str, Any], csrf_token: str = "") -> Dict[str, str]:
    """把参数按网易云 weapi 的方式加密。

    发送验证码 / 手机号登录的接口会校验 encSecKey，明文请求会返回
    “无权限访问. ENC”，所以必须走这套 AES + RSA。
    """
    data = dict(payload)
    data.setdefault("csrf_token", csrf_token or "")
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    secret = "".join(secrets.choice(_WEB_CHARS) for _ in range(16))
    first = _aes_base64(raw, _WEB_PRESET_KEY)
    params = _aes_base64(first.encode("utf-8"), secret.encode("utf-8"))
    # 网易云用的是"裸 RSA"（modPow），不是 PKCS#1 填充；用 PKCS#1 会返回空响应。
    message = int(secret[::-1].encode("utf-8").hex(), 16)
    enc_sec_key = format(
        pow(message, int(_WEB_PUBLIC_KEY, 16), int(_WEB_MODULUS, 16)), "x"
    ).zfill(256)
    return {"params": params, "encSecKey": enc_sec_key}


def _json(response: httpx.Response) -> Dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise NeteaseError("网易云返回的内容解析失败，接口可能变了") from exc
    if not isinstance(data, dict):
        raise NeteaseError("网易云返回的内容格式不对")
    return data


def _cookie_pairs(cookies: httpx.Cookies) -> List[Tuple[str, str]]:
    """按 CookieJar 读取，避免同名 Cookie 触发 httpx.CookieConflict。

    网易云一次会下发多个域/路径下的 MUSIC_A_T，直接调 cookies.items()
    会抛异常；这里按名字去重，保留最后一条。
    """
    jar = getattr(cookies, "jar", None)
    if jar is None:
        return list(cookies.items())
    return [(item.name, item.value) for item in jar]


def _join_cookies(pairs: List[Tuple[str, str]]) -> str:
    values: Dict[str, str] = {}
    for name, value in pairs:
        values[name] = value
    return "; ".join("%s=%s" % (name, value) for name, value in values.items())


def _cookies_from_response(response: httpx.Response) -> str:
    pairs: List[Tuple[str, str]] = []
    for header in response.headers.get_list("set-cookie"):
        pair = header.split(";", 1)[0]
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        pairs.append((name.strip(), value.strip()))
    return _join_cookies(pairs)


def _cookie_string(cookies: httpx.Cookies) -> str:
    return _join_cookies(_cookie_pairs(cookies))


def _qr_image(url: str) -> str:
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=4)
    buffer = io.BytesIO()
    image.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return "data:image/svg+xml;base64," + encoded


async def _weapi_request(
    url: str, payload: Dict[str, Any], cookie: str = "", csrf: str = ""
) -> Tuple[httpx.Response, Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
        ) as client:
            response = await client.post(
                url, data=weapi_payload(payload, csrf), headers=_headers(cookie)
            )
    except httpx.HTTPError as exc:
        raise NeteaseError("连接网易云超时了，检查一下网络再试") from exc
    if response.status_code != 200:
        raise NeteaseError("网易云暂时没响应（HTTP %s）" % response.status_code)
    return response, _json(response)


def _https(url: str) -> str:
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return url


def _map_song(song: Dict[str, Any]) -> Dict[str, Any]:
    artists = [item.get("name", "") for item in (song.get("ar") or song.get("artists") or [])]
    album = song.get("al") or song.get("album") or {}
    privilege = song.get("privilege") or {}
    fee = song.get("fee", privilege.get("fee", 0))
    duration = song.get("dt") or song.get("duration") or 0
    return {
        "id": int(song.get("id") or 0),
        "name": song.get("name") or "未知歌曲",
        "artists": " / ".join([name for name in artists if name]) or "未知歌手",
        "album": album.get("name") or "",
        "cover": _https(album.get("picUrl") or ""),
        "duration": int(duration / 1000),
        "vip": fee in (1, 4, 100),
    }


async def search(keyword: str, cookie: str = "", limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    keyword = (keyword or "").strip()
    if not keyword:
        raise NeteaseError("请输入歌名、歌手或关键词")
    limit = max(1, min(int(limit), 30))
    offset = max(0, int(offset))
    form = {
        "s": keyword,
        "type": "1",
        "limit": str(limit),
        "offset": str(offset),
        "total": "true",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
        ) as client:
            response = await client.post(SEARCH_URL, data=form, headers=_headers(cookie))
    except httpx.HTTPError as exc:
        raise NeteaseError("连接网易云超时了，检查一下网络再试") from exc

    if response.status_code != 200:
        raise NeteaseError("网易云暂时没响应（HTTP %s）" % response.status_code)
    try:
        data = response.json()
    except ValueError as exc:
        raise NeteaseError("网易云返回的内容解析失败，接口可能变了") from exc

    code = data.get("code")
    if code not in (None, 200):
        raise NeteaseError(str(data.get("msg") or data.get("message") or "网易云返回错误（%s）" % code))
    result = data.get("result") or {}
    songs: List[Dict[str, Any]] = result.get("songs") or []
    return {
        "songs": [_map_song(song) for song in songs if song.get("id")],
        "total": int(result.get("songCount") or len(songs)),
    }


async def probe(cookie: str) -> Tuple[bool, str, str]:
    """验证 Cookie 是否有效，返回 (是否有效, 提示, 昵称)。"""
    cookie = normalize_cookie(cookie)
    if not cookie_usable(cookie):
        return False, "Cookie 看起来不完整，至少要包含 MUSIC_U", ""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
        ) as client:
            response = await client.get(
                ACCOUNT_URL,
                params={"timestamp": int(time.time() * 1000)},
                headers=_headers(cookie),
            )
    except httpx.HTTPError:
        return False, "连不上网易云，检查网络后再试", ""

    if response.status_code != 200:
        return False, "网易云返回 HTTP %s" % response.status_code, ""
    try:
        data = response.json()
    except ValueError:
        return False, "网易云返回内容解析失败", ""

    profile = data.get("profile") or {}
    account = data.get("account") or {}
    nickname = profile.get("nickname") or account.get("userName") or ""
    if nickname or profile.get("userId") or account.get("id"):
        return True, "登录状态有效" + ("：" + nickname if nickname else ""), nickname
    return False, "Cookie 无效或已过期，请重新复制 MUSIC_U", ""


async def qr_create() -> Dict[str, Any]:
    """生成扫码登录二维码。返回 unikey、二维码图片和轮询需要的会话 Cookie。"""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
        ) as client:
            try:
                await client.get("https://music.163.com/", headers=_headers())
            except httpx.HTTPError:
                pass
            session = _cookie_string(client.cookies)
            csrf = csrf_from_cookie(session)
            response = await client.post(
                QR_UNIKEY_URL,
                data=weapi_payload({"type": "1"}, csrf),
                headers=_headers(session),
            )
            session = _cookie_string(client.cookies)
    except httpx.HTTPError as exc:
        raise NeteaseError("连接网易云超时了，检查一下网络再试") from exc
    if response.status_code != 200:
        raise NeteaseError("网易云暂时没响应（HTTP %s）" % response.status_code)

    data = _json(response)
    key = data.get("unikey") or ""
    if data.get("code") != 200 or not key:
        raise NeteaseError(str(data.get("message") or data.get("msg") or "生成二维码失败"))

    url = "https://music.163.com/login?codekey=" + quote(key)
    try:
        image = _qr_image(url)
    except Exception as exc:  # 二维码库异常时仍然把 key 返回，前端可退回手动 Cookie
        raise NeteaseError("二维码生成失败，请刷新重试") from exc
    return {
        "key": key,
        "url": url,
        "image": image,
        "session": session,
        "expires_in": 180,
    }


async def qr_status(key: str, session: str = "") -> Dict[str, Any]:
    """轮询扫码状态。成功时返回网易云 Cookie，由 API 层保存，不下发给前端。"""
    key = (key or "").strip()
    if not key:
        raise NeteaseError("二维码参数不对，请重新生成")
    cookie = session or ""
    if cookie and "=" not in cookie:
        cookie = "NMTID=" + cookie
    csrf = csrf_from_cookie(cookie)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
        ) as client:
            response = await client.post(
                QR_POLL_URL,
                data=weapi_payload({"key": key, "type": "1"}, csrf),
                headers=_headers(cookie),
            )
    except httpx.HTTPError as exc:
        raise NeteaseError("连接网易云超时了，检查一下网络再试") from exc
    if response.status_code != 200:
        raise NeteaseError("网易云暂时没响应（HTTP %s）" % response.status_code)

    data = _json(response)
    code = data.get("code")
    if code == 801:
        return {"status": "waiting", "message": "等待扫码"}
    if code == 802:
        return {"status": "scanned", "message": "已扫码，请在手机上确认"}
    if code == 800:
        return {"status": "expired", "message": "二维码已过期"}
    if code in (200, 803):
        raw_cookie = data.get("cookie")
        merged = raw_cookie if isinstance(raw_cookie, str) else ""
        if not cookie_usable(merged):
            parts = [cookie] if cookie else []
            extra = _cookies_from_response(response)
            if extra:
                parts.append(extra)
            merged = "; ".join(parts)
        if not cookie_usable(merged):
            raise NeteaseError("登录成功但没拿到 MUSIC_U，请重新生成二维码")
        return {"status": "confirmed", "cookie": merged, "message": "登录成功"}
    raise NeteaseError(str(data.get("message") or data.get("msg") or "二维码状态异常"))


def _prune_phone_sessions() -> None:
    now = time.time()
    for key, item in list(_PHONE_SESSIONS.items()):
        if now - item.get("created", 0) > _PHONE_SESSION_TTL:
            _PHONE_SESSIONS.pop(key, None)


async def send_captcha(
    phone: str, country_code: str = "86", session_key: str = ""
) -> Dict[str, Any]:
    """给手机号发网易云登录验证码，并把这次会话留给后面的登录请求。"""
    _prune_phone_sessions()
    payload = {"cellphone": phone, "ctcode": country_code}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
        ) as client:
            try:
                await client.get("https://music.163.com/", headers=_headers())
            except httpx.HTTPError:
                pass
            cookie = _cookie_string(client.cookies)
            csrf = csrf_from_cookie(cookie)
            response = await client.post(
                SMS_URL, data=weapi_payload(payload, csrf), headers=_headers(cookie)
            )
            cookie = _cookie_string(client.cookies)
    except httpx.HTTPError as exc:
        raise NeteaseError("连接网易云超时了，检查一下网络再试") from exc
    if response.status_code != 200:
        raise NeteaseError("网易云暂时没响应（HTTP %s）" % response.status_code)

    data = _json(response)
    code = data.get("code")
    if code != 200:
        raise NeteaseError(str(data.get("message") or data.get("msg") or "验证码发送失败"))
    if session_key:
        _PHONE_SESSIONS[session_key] = {"cookie": cookie, "created": time.time()}
    return {"message": data.get("message") or "验证码已发送，注意查收短信"}


async def phone_login(
    phone: str, captcha: str, country_code: str = "86", session_key: str = ""
) -> Dict[str, Any]:
    """手机号 + 短信验证码登录，返回 Cookie 和昵称。"""
    _prune_phone_sessions()
    cookie = (_PHONE_SESSIONS.get(session_key) or {}).get("cookie", "") if session_key else ""
    if not cookie:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
            ) as client:
                try:
                    await client.get("https://music.163.com/", headers=_headers())
                except httpx.HTTPError:
                    pass
                cookie = _cookie_string(client.cookies)
        except httpx.HTTPError:
            cookie = ""
    csrf = csrf_from_cookie(cookie)
    response, data = await _weapi_request(
        PHONE_LOGIN_URL,
        {
            "phone": phone,
            "countrycode": country_code,
            "captcha": captcha,
            "rememberLogin": "true",
        },
        cookie,
        csrf,
    )
    code = data.get("code")
    if code != 200:
        raise NeteaseError(str(data.get("message") or data.get("msg") or "登录失败，验证码可能不对"))

    raw_cookie = data.get("cookie")
    cookie = raw_cookie if isinstance(raw_cookie, str) else ""
    if not cookie_usable(cookie):
        cookie = _cookies_from_response(response)
    if not cookie_usable(cookie):
        raise NeteaseError("登录成功但没拿到 MUSIC_U，请重试")

    if session_key:
        _PHONE_SESSIONS.pop(session_key, None)

    profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    nickname = profile.get("nickname") or ""
    return {"cookie": cookie, "nickname": nickname, "message": "登录成功"}


async def resolve_audio(song_id: int, cookie: str = "") -> str:
    song_id = int(song_id)
    if song_id <= 0:
        raise NeteaseError("歌曲 ID 不对")
    params = {"id": str(song_id), "ids": "[%d]" % song_id, "br": "320000"}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=6.0), follow_redirects=True
        ) as client:
            response = await client.get(PLAYER_URL, params=params, headers=_headers(cookie))
    except httpx.HTTPError as exc:
        raise NeteaseError("连接网易云超时了，检查一下网络再试") from exc

    if response.status_code != 200:
        raise NeteaseError("网易云暂时没响应（HTTP %s）" % response.status_code)
    try:
        data = response.json()
    except ValueError as exc:
        raise NeteaseError("网易云返回的内容解析失败，接口可能变了") from exc

    items = data.get("data") or []
    item = items[0] if items else {}
    url = item.get("url") or ""
    if url:
        return _https(url)

    if item.get("code") == 404 or data.get("code") == 404:
        raise NeteaseError("这首歌没有版权或已下架")
    if not cookie_usable(cookie):
        raise NeteaseError("这首歌需要网易云登录，先在设置里填 MUSIC_U Cookie")
    raise NeteaseError("这首歌暂时拿不到播放地址（可能需要 VIP 或已下架）")


async def open_stream(
    song_id: int, cookie: str = "", range_header: Optional[str] = None
) -> Tuple[httpx.AsyncClient, httpx.Response]:
    """打开上游音频流。调用方负责在读完/出错后关闭 response 和 client。"""
    url = await resolve_audio(song_id, cookie)
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(20.0, connect=10.0, read=None), follow_redirects=True
    )
    headers = {"User-Agent": UA, "Referer": REFERER}
    if range_header:
        headers["Range"] = range_header
    try:
        request = client.build_request("GET", url, headers=headers)
        response = await client.send(request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise NeteaseError("音频服务器连接失败，稍后再试") from exc

    content_type = (response.headers.get("content-type") or "").lower()
    bad_body = "text/html" in content_type or "application/json" in content_type
    if response.status_code not in (200, 206) or bad_body:
        status_code = response.status_code
        await response.aclose()
        await client.aclose()
        if status_code in (401, 403):
            raise NeteaseError("网易云要求登录后才能播放这首歌，请先填 Cookie")
        if status_code == 404 or bad_body:
            raise NeteaseError("这首歌没有版权或已下架")
        raise NeteaseError("这首歌暂时放不了（HTTP %s）" % status_code)
    return client, response
