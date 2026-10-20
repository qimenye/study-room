"""端到端冒烟测试：不启动服务器、不占端口，直接跑完整业务链路。

用法（在 backend 目录下）：
    ..\.venv\Scripts\python.exe smoke_test.py

覆盖：健康检查 → 注册/登录 → 房间列表/创建/加入 → WebSocket 实时同步
      → 计时开始/暂停/继续/结束 → 统计/热力图/排行榜 → AI 智能体接口

测试使用独立的 smoke_test.db，跑完自动删除，不影响正式数据。
"""

import os
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

# 数据库放在系统临时目录，避免污染仓库；可用 SMOKE_DB 环境变量指定路径
import tempfile

DB_PATH = pathlib.Path(os.environ.get("SMOKE_DB") or (pathlib.Path(tempfile.gettempdir()) / "studyroom_smoke.db"))
if DB_PATH.exists():
    DB_PATH.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + DB_PATH.as_posix()
os.environ["LLM_PROVIDER"] = "mock"
os.environ["JWT_SECRET"] = "smoke-test-secret-0123456789abcdefghijklmnopqrstuvwxyz"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

passed = []
failed = []


def check(name, condition, extra=""):
    if condition:
        passed.append(name)
        print("  PASS  %s" % name)
    else:
        failed.append(name)
        print("  FAIL  %s %s" % (name, extra))


def main():
    with TestClient(app) as client:
        print("[1] 健康检查与冷启动数据")
        health = client.get("/api/health")
        check("健康检查 200", health.status_code == 200, health.text)
        check("无 Key 时 AI 走本地兜底", health.json().get("llm_enabled") is False)

        print("[2] 注册 / 登录 / 鉴权")
        r1 = client.post("/api/auth/register", json={"username": "alice", "password": "pass1234", "nickname": "小艾"})
        check("注册返回 201", r1.status_code == 201, r1.text)
        r2 = client.post("/api/auth/register", json={"username": "bob", "password": "pass1234"})
        check("第二个用户注册成功", r2.status_code == 201, r2.text)
        dup = client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
        check("重复用户名被拒 400", dup.status_code == 400, dup.text)
        bad = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
        check("错误密码被拒 400", bad.status_code == 400, bad.text)
        login = client.post("/api/auth/login", json={"username": "alice", "password": "pass1234"})
        check("登录成功", login.status_code == 200, login.text)
        token_a = login.json()["access_token"]
        token_b = r2.json()["access_token"]
        ha = {"Authorization": "Bearer " + token_a}
        hb = {"Authorization": "Bearer " + token_b}

        no_auth = client.get("/api/rooms")
        check("未带 token 访问被拒 403", no_auth.status_code in (401, 403), no_auth.text)
        me = client.get("/api/users/me", headers=ha)
        check("读取个人资料", me.status_code == 200 and me.json()["nickname"] == "小艾", me.text)
        patched = client.patch("/api/users/me", json={"nickname": "小艾同学"}, headers=ha)
        check("修改昵称", patched.status_code == 200 and patched.json()["nickname"] == "小艾同学", patched.text)

        print("[3] 房间")
        rooms = client.get("/api/rooms", headers=ha).json()
        check("官方常驻房间已建好（4 个）", len([x for x in rooms if x["is_official"]]) == 4, str(len(rooms)))
        created = client.post(
            "/api/rooms",
            json={"name": "冒烟测试房", "topic": "编程", "description": "测试用", "max_users": 3},
            headers=ha,
        )
        check("创建房间", created.status_code == 201, created.text)
        room_id = created.json()["id"]
        joined = client.post("/api/rooms/%d/join" % room_id, headers=hb)
        check("第二个人加入房间", joined.status_code == 200, joined.text)
        detail = client.get("/api/rooms/%d" % room_id, headers=ha).json()
        check("房间详情含 2 名成员", len(detail["members"]) == 2, str(detail["members"]))

        print("[4] WebSocket 实时同步")
        with client.websocket_connect("/ws/room/%d?token=%s" % (room_id, token_a)) as ws:
            first = ws.receive_json()
            check("进房收到 room_state", first.get("type") == "room_state", str(first)[:200])
            check("room_state 带成员列表", len(first.get("members", [])) >= 1)
            check("进房有 AI 欢迎语", bool(first.get("welcome", {}).get("message")), str(first.get("welcome")))
            ws.send_json({"type": "ping"})
            check("心跳返回 pong", ws.receive_json().get("type") == "pong")
            ws.send_json({"type": "status", "status": "focusing"})
            status_msg = ws.receive_json()
            check("状态切换被广播", status_msg.get("type") == "status_change" and status_msg.get("status") == "focusing", str(status_msg)[:200])
            ws.send_json({"type": "status", "status": "sleeping"})
            check("非法状态被拒", ws.receive_json().get("code") == "bad_status")
            ws.send_json({"type": "chat", "content": "一起来刷题"})
            chat_msg = ws.receive_json()
            check("房间发言被广播", chat_msg.get("type") == "chat" and chat_msg.get("content") == "一起来刷题", str(chat_msg)[:200])

        print("[5] 专注计时（时长以服务端为准）")
        unauthorized_ws = client.post("/api/rooms/%d/join" % room_id, headers=ha)
        check("HTTP 入房幂等", unauthorized_ws.status_code == 200, unauthorized_ws.text)

        started = client.post("/api/sessions/start", json={"room_id": room_id, "mode": "pomodoro", "planned_minutes": 25}, headers=ha)
        check("开始专注", started.status_code == 200, started.text)
        session_id = started.json()["id"]
        again = client.post("/api/sessions/start", json={"room_id": room_id, "mode": "pomodoro", "planned_minutes": 25}, headers=ha)
        check("重复开始被拒 409", again.status_code == 409, again.text)

        import time

        time.sleep(1.2)
        paused = client.post("/api/sessions/%d/pause" % session_id, headers=ha)
        check("暂停", paused.status_code == 200 and paused.json()["status"] == "paused", paused.text)
        time.sleep(1.2)
        resumed = client.post("/api/sessions/%d/resume" % session_id, headers=ha)
        check("继续", resumed.status_code == 200 and resumed.json()["status"] == "running", resumed.text)
        check("暂停时长已累计", resumed.json()["paused_total"] >= 1, str(resumed.json()))

        active = client.get("/api/sessions/active", headers=ha).json()
        check("可恢复进行中的会话", active["session"] is not None and active["elapsed_seconds"] >= 0, str(active)[:200])

        time.sleep(1.1)
        ended = client.post("/api/sessions/%d/end" % session_id, headers=ha)
        check("结束专注", ended.status_code == 200 and ended.json()["status"] == "finished", ended.text)
        duration = ended.json()["duration"]
        check("净时长扣除了暂停（约 2 秒而非 4 秒）", 1 <= duration <= 3, "duration=%s" % duration)
        ended_again = client.post("/api/sessions/%d/end" % session_id, headers=ha)
        check("重复结束幂等", ended_again.status_code == 200 and ended_again.json()["duration"] == duration, ended_again.text)
        check("用户累计时长已更新", client.get("/api/users/me", headers=ha).json()["total_duration"] >= duration)

        print("[6] 统计 / 热力图 / 排行榜")
        stats = client.get("/api/sessions/stats", headers=ha).json()
        check("统计包含今日时长", stats["today_duration"] >= duration, str(stats))
        check("统计包含连续打卡", stats["streak_days"] >= 1, str(stats))
        heat = client.get("/api/sessions/heatmap", params={"days": 30}, headers=ha).json()
        check("热力图返回 30 天", len(heat["days"]) == 30, str(len(heat["days"])))
        check("热力图最后一天是今天且有数据", heat["days"][-1]["duration"] >= duration, str(heat["days"][-1]))
        records = client.get("/api/sessions/records", params={"period": "today"}, headers=ha).json()
        check("今日明细包含本次记录", len(records) == 1 and records[0]["id"] == session_id, str(records)[:200])
        ranking = client.get("/api/ranking", params={"period": "today"}, headers=ha).json()
        check("排行榜包含自己", any(x["user_id"] == me.json()["id"] for x in ranking), str(ranking)[:200])

        print("[7] AI 智能体（无 Key 兜底）")
        enc = client.post("/api/agent/encourage", json={"room_id": room_id, "scene": "finish", "duration_minutes": 25}, headers=ha)
        check("陪伴鼓励返回文案", enc.status_code == 200 and len(enc.json()["message"]) > 0, enc.text)
        check("标注了兜底来源", enc.json()["source"] == "template", enc.text)
        report = client.get("/api/agent/report", headers=ha)
        check("生成学习报告", report.status_code == 200 and "学习报告" in report.json()["content"], report.text[:200])
        plan = client.post("/api/agent/plan", json={"goal": "考研数学强化", "weeks": 4, "hours_per_week": 12}, headers=ha)
        check("生成学习计划", plan.status_code == 200 and plan.json()["plan_id"] > 0, plan.text[:200])
        check("计划正文包含周次", "第 4 周" in plan.json()["content"], plan.text[:300])
        plans = client.get("/api/agent/plans", headers=ha).json()
        check("历史计划可回看", len(plans) == 1, str(len(plans)))
        chat = client.post("/api/agent/chat", json={"message": "我学不进去怎么办"}, headers=ha)
        check("AI 对话有回复", chat.status_code == 200 and len(chat.json()["reply"]) > 0, chat.text[:200])

        print("[8] 权限与边界")
        foreign = client.get("/api/rooms/%d" % room_id, headers=ha)
        check("无关用户也能看房间", foreign.status_code == 200)
        delete_by_bob = client.delete("/api/rooms/%d" % room_id, headers=hb)
        check("非房主删除房间被拒 403", delete_by_bob.status_code == 403, delete_by_bob.text)
        delete_official = client.delete("/api/rooms/1", headers=ha)
        check("官方房间不可删除 403", delete_official.status_code == 403, delete_official.text)
        cross = client.post("/api/sessions/%d/end" % session_id, headers=hb)
        check("不能操作他人会话 404", cross.status_code == 404, cross.text)

        full_room = client.post(
            "/api/rooms",
            json={"name": "满员房", "topic": "自习", "max_users": 2},
            headers=ha,
        ).json()
        client.post("/api/rooms/%d/join" % full_room["id"], headers=ha)
        client.post("/api/rooms/%d/join" % full_room["id"], headers=hb)
        third = client.post("/api/auth/register", json={"username": "carol", "password": "pass1234"})
        token_c = third.json()["access_token"]
        hc = {"Authorization": "Bearer " + token_c}
        r = client.post("/api/rooms/%d/join" % full_room["id"], headers=hc)
        check("人数上限生效 409", r.status_code == 409, r.text)
        check("满员后仍可查看房间", client.get("/api/rooms/%d" % full_room["id"], headers=hc).status_code == 200)

        print("[9] 模型设置（网页里自带的 API Key）")
        s0 = client.get("/api/settings/llm", headers=ha)
        check("读取模型设置 200", s0.status_code == 200, s0.text[:200])
        check("未配置时来源为 none", s0.json().get("source") == "none", str(s0.json().get("source")))
        check("返回 provider 预设", len(s0.json().get("providers", [])) >= 5)
        check("响应里不含 Key 字段", "api_key" not in s0.text)

        too_short = client.put(
            "/api/settings/llm",
            json={"provider": "deepseek", "model": "deepseek-chat", "api_key": "short"},
            headers=ha,
        )
        check("过短的 Key 被拒 400", too_short.status_code == 400, too_short.text)
        bad_url = client.put(
            "/api/settings/llm",
            json={"provider": "deepseek", "model": "deepseek-chat", "base_url": "ftp://x"},
            headers=ha,
        )
        check("非法接口地址被拒 400", bad_url.status_code == 400, bad_url.text)
        bad_provider = client.put(
            "/api/settings/llm",
            json={"provider": "not-a-provider", "model": "m", "api_key": "sk-1234567890"},
            headers=ha,
        )
        check("未知 provider 被拒 400", bad_provider.status_code == 400, bad_provider.text)
        no_key = client.put(
            "/api/settings/llm",
            json={"provider": "deepseek", "model": "deepseek-chat"},
            headers=ha,
        )
        check("没有 Key 时不允许启用", no_key.status_code == 400, no_key.text)

        saved = client.put(
            "/api/settings/llm",
            json={
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": "sk-test-1234567890abcdef",
            },
            headers=ha,
        )
        check("保存 Key 成功", saved.status_code == 200, saved.text[:200])
        check("保存后来源为用户", saved.json().get("source") == "user")
        check("配好后 llm_ready 为真", saved.json().get("llm_ready") is True)
        check(
            "只回掩码不回明文",
            "sk-test-1234567890abcdef" not in saved.text
            and saved.json().get("key_masked") == "sk-te***cdef",
            str(saved.json().get("key_masked")),
        )
        check(
            "别人的配置与我无关",
            client.get("/api/settings/llm", headers=hb).json().get("source") == "none",
        )

        keep = client.put(
            "/api/settings/llm",
            json={"provider": "deepseek", "model": "deepseek-reasoner"},
            headers=ha,
        )
        check(
            "不传 Key 时保留原 Key",
            keep.json().get("has_key") is True and keep.json().get("model") == "deepseek-reasoner",
        )

        cleared = client.delete("/api/settings/llm", headers=ha)
        check(
            "清除后回落到服务端配置",
            cleared.status_code == 200 and cleared.json().get("source") == "none",
        )

        print("[10] 网易云音乐（搜索 / Cookie / 音频代理）")
        m0 = client.get("/api/settings/music", headers=ha)
        check("读取网易云设置 200", m0.status_code == 200, m0.text[:200])
        check("默认没有 Cookie", m0.json().get("has_cookie") is False, m0.text[:200])
        check("返回昵称字段", m0.json().get("nickname") == "", m0.text[:200])
        check("网易云设置需要登录", client.get("/api/settings/music").status_code in (401, 403))

        bad_cookie = client.put(
            "/api/settings/music", json={"cookie": "short"}, headers=ha
        )
        check("过短的 Cookie 被拒 400", bad_cookie.status_code == 400, bad_cookie.text)
        empty_cookie = client.put("/api/settings/music", json={"cookie": ""}, headers=ha)
        check("空 Cookie 被拒 400", empty_cookie.status_code == 400, empty_cookie.text)

        fake_cookie = "MUSIC_U=fake-cookie-1234567890abcdef"
        m1 = client.put("/api/settings/music", json={"cookie": fake_cookie}, headers=ha)
        check("保存 Cookie 成功", m1.status_code == 200, m1.text[:200])
        check(
            "保存后只回掩码",
            m1.json().get("has_cookie") is True
            and m1.json().get("source") == "user"
            and fake_cookie not in m1.text
            and m1.json().get("cookie_masked", "").endswith("cdef"),
            m1.text[:200],
        )
        check(
            "别人的网易云 Cookie 与我无关",
            client.get("/api/settings/music", headers=hb).json().get("has_cookie") is False,
        )

        m2 = client.put("/api/settings/music", json={}, headers=ha)
        check("不传 Cookie 时保持原样", m2.json().get("has_cookie") is True, m2.text[:200])
        m3 = client.delete("/api/settings/music", headers=ha)
        check(
            "清除 Cookie 后回到未登录态",
            m3.status_code == 200 and m3.json().get("has_cookie") is False,
            m3.text[:200],
        )

        check(
            "搜索必须登录",
            client.get("/api/music/search", params={"q": "雨声"}).status_code in (401, 403),
        )
        check(
            "搜索关键词不能为空",
            client.get("/api/music/search", params={"q": ""}, headers=ha).status_code == 422,
        )
        check(
            "音频流必须登录",
            client.get("/api/music/stream/1").status_code in (401, 403),
        )
        check(
            "非法歌曲 ID 被拒 400",
            client.get("/api/music/stream/0", headers=ha).status_code == 400,
        )
        check(
            "扫码登录需要登录本站",
            client.post("/api/music/login/qr").status_code in (401, 403),
        )
        check(
            "扫码状态接口需要登录本站",
            client.get(
                "/api/music/login/qr/status", params={"key": "0123456789abcdef"}
            ).status_code
            in (401, 403),
        )
        bad_phone = client.post(
            "/api/music/login/captcha", json={"phone": "12345"}, headers=ha
        )
        check("验证码手机号格式校验 400", bad_phone.status_code == 400, bad_phone.text)
        bad_phone_login = client.post(
            "/api/music/login/phone",
            json={"phone": "12345", "captcha": "0000"},
            headers=ha,
        )
        check("手机登录手机号格式校验 400", bad_phone_login.status_code == 400, bad_phone_login.text)
        bad_captcha = client.post(
            "/api/music/login/phone",
            json={"phone": "13800000000", "captcha": "00"},
            headers=ha,
        )
        check("短信验证码格式校验 400", bad_captcha.status_code == 400, bad_captcha.text)

    print()
    print("=" * 56)
    print("通过 %d 项，失败 %d 项" % (len(passed), len(failed)))
    if failed:
        print("失败清单：")
        for name in failed:
            print("  -", name)
    print("=" * 56)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        if DB_PATH.exists():
            try:
                DB_PATH.unlink()
            except OSError:
                pass
    sys.exit(code)
