# 线上自习室（MVP 骨架）

一个基于 **FastAPI + Vue 3** 的线上虚拟自习室，房间实时同步 + 番茄钟 + 白噪音 + 学习统计 + AI 学习陪伴。

当前状态：**MVP 闭环的可运行骨架已搭好**，前后端代码、目录结构、数据库模型、接口、WebSocket 协议全部就位，装完依赖即可跑起来。

- 原始需求：`docs/原始需求-自习室软件.txt`
- 评估与注意事项（**建议先读这份**）：`docs/项目评估与注意事项.md`
- 技术选型取舍：`docs/技术选型说明.md`

---

## 一、目录结构

```
自习室软甲/
├── README.md
├── setup.bat                  # 一键初始化（建 venv + 装依赖）
├── start.bat                  # ★ 一键启动（自动重建前端 + 起后端 + 开浏览器）
├── run-backend.bat            # 一键启动的实现（start.bat 就是调它）
├── run-frontend.bat           # 开发模式前端（5173 热更新）
├── build-frontend.bat         # 手动构建前端（平时不用，start.bat 会自动判断）
├── docs/
│   ├── 原始需求-自习室软件.txt
│   ├── 项目评估与注意事项.md
│   └── 技术选型说明.md
├── backend/
│   ├── requirements.txt
│   ├── smoke_test.py          # 端到端自检（86 项断言，不用起服务）
│   ├── .env.example           # 复制成 .env 后按需修改
│   └── app/
│       ├── main.py            # 入口：路由 / CORS / WebSocket / 心跳清理任务
│       ├── config.py          # 环境变量配置
│       ├── database.py        # SQLAlchemy 连接与建表
│       ├── seed.py            # 官方常驻房间（解决冷启动空房间）
│       ├── core/              # security(JWT/bcrypt) / deps / timeutil / ratelimit
│       ├── models/            # User / Room / RoomMember / StudySession / AgentMessage / StudyPlan / MusicSetting
│       ├── schemas/           # Pydantic 校验
│       ├── api/               # auth / users / rooms / sessions / ranking / agent / settings / music
│       ├── services/          # stats 统计聚合 / netease 网易云代理 / llm_settings / music_settings
│       ├── websocket/         # room_manager（连接与心跳）+ routes（WS 协议）
│       └── agents/            # llm / companion / report / planner / host
└── frontend/
    ├── package.json
    ├── vite.config.js         # 已配好 /api 与 /ws 代理
    └── src/
        ├── api/               # fetch 封装 + 各模块接口
        ├── socket/            # WebSocket 封装（自动重连 + 心跳）
        ├── stores/            # Pinia：user / room / timer
        ├── workers/           # 防节流计时 Worker
        ├── components/        # RoomCard / MemberSeat / PomodoroTimer / WhiteNoise / MusicPlayer / MusicVisualizer / NeteaseLogin / Heatmap / AgentChat
        │                      # + AppHeader / AppIcon / Backdrop / WallpaperPicker / PageScrollHint
        │                      # + PageRail / LlmSettings
        ├── composables/       # useWallpaper（壁纸）/ useScrollPaging（滚动翻页）
        ├── pages/             # Login / RoomList / RoomDetail / Records / Ranking / Agent
        └── utils/format.js    # 时长格式化 + UTC 时间解析
```

---

## 二、快速开始

### 首次初始化

```bat
setup.bat
```

它会做三件事：创建 `.venv`、安装后端依赖、安装前端依赖。

也可以手动执行：

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend && npm install
```

### 启动

```bat
start.bat           :: 就双击这个（等价于 run-backend.bat）
run-frontend.bat    :: 开发模式，前端 http://127.0.0.1:5173（改代码热更新）
```

`start.bat` 每次会做三件事，保证你看到的永远是最新状态：

1. 检查 `.venv` 和 `frontend\node_modules`（缺了就提示先跑 `setup.bat`）；
2. 对比 `frontend\src` 和 `frontend\dist` 的修改时间——源码更新过就自动 `npm run build` 重建，没变就跳过（通常 1 秒）；
3. 启动后端 http://127.0.0.1:8000（接口文档 `/docs`），等服务就绪后自动打开浏览器。

所以**改完前端代码不用再手动构建**，双击一次 `start.bat` 就是最新的；关掉那个黑窗口就停服务。

如果 8000 端口已经有服务在跑，它不会重复启动，只会打开浏览器；这种情况要是刚改过后端代码，去原来那个窗口按 `Ctrl+C` 重启一次。

想同时跑开发模式（5173 热更新 + 8000 后端）：`run-backend.bat` + `run-frontend.bat`，浏览器访问 http://127.0.0.1:5173。首次使用先注册账号。

### 想手动构建 / 排查

`build-frontend.bat` 仍然能用，等价于进 `frontend` 目录跑下面这行，产物落在 `frontend\dist`（构建会顺手清空 dist 里的旧文件）：

```bat
cd /d F:\自习室软甲\frontend       :: 先进入 frontend 目录，注意是 frontend，不是项目根目录
npm run build
```

命令要在**终端**里跑（PowerShell 或 CMD 都行），不是在浏览器或别的地方。平时不用单独跑，`start.bat` 会自动判断。

### 界面：壁纸与滚动翻页

- **背景壁纸**：右上角调色盘按钮切换，内置 7 套（自动 / 深夜 / 极光 / 暖灯 / 森林 / 樱雾 / 纯墨）。全部用 CSS 渐变 + 模糊光斑生成，不加载任何图片，多高的分辨率都不糊；「自动」会按当前时间段选一套。选择存在 localStorage，刷新不丢。
- **自己的图片壁纸**：同一个面板里点「+ 添加」，可以直接**上传本地图片**（会自动压到 1920px 再存），也可以**粘贴图片链接**。最多存 6 张，图片只存在你自己的浏览器里，不会上传到服务器；选中照片壁纸后会多出一个「遮罩强度」滑块，用来压暗背景保证文字看得清。
- **上下滚动切换页面**：自习室 → 学习记录 → 排行榜 → AI 助手按顺序排列。
  - 滚到页面底部后继续往下滚 = 下一页；在页面顶部继续往上滚 = 上一页，两个方向都有进度圆环和文字提示，点提示也能跳。
  - 滚到一半停手，进度圆环会自动回弹清零，不会以"卡住"的半截状态停在屏幕上；换页后也会立刻清零。
  - 右侧（宽屏）还有一条页码导轨：上下两个箭头翻页，中间的点直接跳到对应页面。
  - 聊天记录、报告正文这类内部可滚动的区域不会误触发翻页；它们滚到头之后，继续滚就正常翻页。

### AI：在网页里填自己的 API Key

「AI 助手」页顶部有「模型设置」，不用再去改 `.env`：

- 选预设（DeepSeek / 通义千问 / 智谱 / OpenAI / 本地 Ollama / 自定义），接口地址和模型名会自动填好，也可以手动改。
- 粘贴 Key → 保存；旁边有「测试连接」，会真的打一次接口并把报错原因翻成人话（Key 不对 / 地址不对 / 被限流）。
- 优先级：**你自己的 Key > 服务端 `.env` > 本地模板兜底**。想撤销就点「清除我的配置」。
- Key 只存在后端数据库里，接口只回掩码（例如 `sk-01***6b6b`），页面拿不到明文，也不会有第二个用户能用上你的额度。
- 模型名建议用 **`deepseek-chat`** 这类对话模型。`deepseek-reasoner` / 名字带 `flash` 的「推理模型」会先把额度花在思考上，生成长计划时容易只思考不回答；真选了它，后端会自动加大额度重试一次。万一还是没答上，聊天框和报告/计划都会**直接写明原因**（而不是给你一段套话），照提示去「测试连接」即可。

### 网易云音乐 + 实时频谱

房间详情页右侧「声音」卡片里，除了原来的白噪音，多了一个「网易云」页签：

- 搜歌名 / 歌手，点结果就能播；有封面、时长、暂停、拖动进度、音量，播完自动下一首。
- 播放区下面是**真实的频谱可视化**：后端把音频同源转发，前端用 `AnalyserNode` 取频域数据画柱状频谱，不是固定动画。
- 点「网易云登录」可以**扫码登录**（用网易云音乐 App 扫二维码，手机上确认）或**手机验证码登录**。登录的是你自己的网易云账号，VIP / 高音质歌曲会用这个账号的权限。
- 登录成功后只把 `MUSIC_U` 等 Cookie 存在本机后端，页面拿不到明文；可以随时「退出登录」。Cookie 会过期，失效时点「验证登录」会直接告诉你。
- 还保留了「手动 Cookie」作为备用：浏览器登录 [music.163.com](https://music.163.com) → F12 → Application/Storage → Cookies → 复制 `MUSIC_U`。
- 用的是网易云网页端接口（非官方），接口调整或版权限制都可能让某首歌放不了；放不了时换一首，或填 Cookie 再试。

### 自检：不用启动服务，直接跑一遍全链路

```bat
cd backend
..\.venv\Scripts\python.exe smoke_test.py
```

覆盖 86 项断言：健康检查 → 注册/登录/鉴权 → 房间增删与人数上限 → WebSocket 实时同步（进房/状态/心跳/发言）→ 番茄钟开始暂停继续结束（含暂停不计入时长）→ 统计/热力图/排行榜 → AI 接口 → 权限与边界（越权删房、操作他人会话等）→ 模型设置（自带 Key 的校验、掩码、隔离与回落）→ 网易云登录参数校验、设置与音乐接口鉴权。

它使用系统临时目录里的独立数据库，跑完自动清理，不会碰你的正式数据。

### 可选：让 AI 用上真实大模型

最省事的做法是**完全不用碰文件**：打开网页 → 「AI 助手」→「模型设置」→ 选服务商、粘贴 Key、点「测试连接」，搞定。

如果你更想让整台服务共用一个 Key，`backend\.env` 也已经建好了（含随机生成的 JWT 密钥），填一个 Key 就能从"模板兜底"切到真实大模型：

```ini
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-你的key        # 只改这一行
```

不填也能用：所有 AI 功能会自动降级为本地模板，接口返回里的 `source` 字段会标明是 `template` 还是 `llm`。

想换成别家，改这三个值即可（都是 OpenAI 兼容协议）：

| provider | LLM_BASE_URL | LLM_MODEL | 备注 |
|----------|--------------|-----------|------|
| `deepseek` | `https://api.deepseek.com/v1` | `deepseek-chat` | 便宜，注册有额度，最推荐 |
| `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | 阿里通义 |
| `glm` | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 智谱，有免费档 |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` | 需要能访问外网 |
| `ollama` | `http://127.0.0.1:11434/v1` | `qwen2.5:7b` | 本地跑，完全免费，不需要 Key |

---

## 三、本机环境注意事项

1. **Anaconda base 的 Python 3.9 不可用**：`_ssl` 模块 DLL 加载失败，pip/httpx 等一切依赖 SSL 的库都会崩。本项目用 `C:\Users\LEGION\anaconda3\envs\py310`（Python 3.10.20）创建 `.venv`，已验证可用。
2. JWT 密钥：HS256 建议不少于 32 字节，生产环境启动时会强制校验（不足直接拒绝启动）；开发环境用内置密钥即可。
3. 本机没有 `py` launcher，`where python` 只指向 Anaconda base。请始终用 `.venv\Scripts\python.exe` 或 `run-backend.bat`。
4. Windows 上 `zoneinfo` 需要 `tzdata` 包，已写进 `requirements.txt`（否则时区换算会退化成 UTC+8）。

---

## 四、已实现 vs 待办

### 第一阶段 MVP

| 功能 | 状态 | 说明 |
|------|------|------|
| 注册 / 登录 / JWT | 已完成 | PyJWT + bcrypt，密码不落明文 |
| 个人主页（昵称/头像/累计时长） | 已完成 | `GET/PATCH /api/users/me`，头像先用字段占位，未做上传 |
| 房间列表 / 创建 / 删除 | 已完成 | 官方常驻房间不可删，房主才有删除权限 |
| 加入 / 离开房间 | 已完成 | `(room_id, user_id)` 唯一约束，重复加入幂等 |
| 成员列表 + 实时状态 | 已完成 | focus/rest/away 三态，心跳 25 秒 |
| 2D 座位图 | 已完成 | 头像占位 + 空位展示，座位号由服务端分配 |
| 番茄钟 / 正计时 | 已完成 | Web Worker 驱动，25/45/自定义 |
| 开始 / 暂停 / 结束 | 已完成 | 暂停时长不计入，时长以服务端为准 |
| 状态实时同步到房间 | 已完成 | WebSocket 广播 |
| 白噪音 / 网易云音乐 | 已完成 | Web Audio 合成 5 种；网易云搜索 + 同源音频流 + 实时频谱 |
| 学习记录 / 热力图 / 排行榜 | 已完成 | 今日/本周/本月/全部，按用户本地时区切分 |
| 番茄钟结束提醒 | 已完成 | 浏览器桌面通知（需授权） |

### 第二阶段（未做，接口已预留）

好友系统、学习小组 PK、动态广场、成就徽章。

### 第三阶段 AI 智能体

| 智能体 | 状态 | 说明 |
|--------|------|------|
| 学习陪伴（打招呼/鼓励/结束总结） | 已完成 | `POST /api/agent/encourage`、`POST /api/agent/chat` |
| 智能学习报告 | 已完成 | `GET /api/agent/report`（本地统计 + 可选大模型点评） |
| 学习计划拆解 | 已完成 | `POST /api/agent/plan`，计划落库可回看 |
| 房间氛围（欢迎语/白噪音推荐） | 已完成 | 进房自动欢迎 + 按房间主题推荐音效 |
| 智能匹配（推荐房间/队友） | 未做 | 需要先有行为数据，放后面做更合适 |

### 明确不做的（受网页端限制）

锁机 / 防玩手机、门禁硬件联动、会员付费。桌面端（Tauri）阶段才能真正做"专注模式"，见评估文档第五节。

---

## 五、核心接口

REST（全部在 `/api` 下，除注册登录外都需要 `Authorization: Bearer <token>`）：

```
POST   /api/auth/register          注册
POST   /api/auth/login             登录
GET    /api/users/me               当前用户
PATCH  /api/users/me               改昵称/头像/时区
GET    /api/rooms                  房间列表（含在线/专注人数）
POST   /api/rooms                  创建房间
GET    /api/rooms/{id}             房间详情（含成员）
DELETE /api/rooms/{id}             删除房间（仅房主）
POST   /api/rooms/{id}/join        加入房间
POST   /api/rooms/{id}/leave       离开房间
POST   /api/sessions/start         开始专注
POST   /api/sessions/{id}/pause    暂停
POST   /api/sessions/{id}/resume   继续
POST   /api/sessions/{id}/end      结束（服务端算时长）
GET    /api/sessions/active        进行中的会话（含服务端算好的已专注秒数）
GET    /api/sessions/records       专注明细
GET    /api/sessions/stats         今日/本周/本月/累计/连续打卡
GET    /api/sessions/heatmap       热力图
GET    /api/ranking                排行榜
POST   /api/agent/encourage        陪伴鼓励
POST   /api/agent/chat             对话
GET    /api/agent/report           学习报告
POST   /api/agent/plan             生成学习计划
GET    /api/agent/plans            历史计划
GET    /api/settings/music         读取网易云 Cookie 状态（只回掩码）
PUT    /api/settings/music         保存 MUSIC_U Cookie
DELETE /api/settings/music         清除 Cookie
POST   /api/settings/music/test    测试 Cookie 是否有效
POST   /api/music/login/qr         生成扫码登录二维码
GET    /api/music/login/qr/status  轮询扫码状态（成功后保存 Cookie）
POST   /api/music/login/captcha    发送手机验证码
POST   /api/music/login/phone      手机号 + 验证码登录
GET    /api/music/search?q=...     搜索网易云歌曲
GET    /api/music/stream/{id}      同源音频流（支持 Range，token 可走 query）
GET    /api/health                 健康检查
```

WebSocket：`ws://127.0.0.1:8000/ws/room/{room_id}?token=<JWT>`

> 浏览器 WebSocket 不能自定义请求头，所以 token 走 query 参数 —— 这是必踩的坑，已在服务端校验。

客户端发：`ping` / `status` / `timer` / `chat`
服务端发：`room_state` / `member_joined` / `member_left` / `status_change` / `timer` / `chat` / `pong` / `agent` / `error`

---

## 六、有意的简化（以及将来怎么升级）

| 简化点 | 现在 | 升级路径 |
|--------|------|----------|
| 数据库 | SQLite | 改 `DATABASE_URL` 切 PostgreSQL |
| 建表 | `create_all` | 换 Alembic 迁移 |
| Redis | 未使用 | 多实例部署时用 Pub/Sub 广播房间消息 |
| 限流 | 进程内滑动窗口 | 换 Redis 计数 |
| 头像 | 字段占位 | 接入对象存储 + 上传接口 |
| 部署 | 本机 | Nginx + 单机 VPS（记得配 WebSocket 升级头） |

另外：`frontend/dist` 已经预先构建好了，后端启动时会自动托管，**所以只双击 `run-backend.bat` 也能在 http://127.0.0.1:8000 用上整站**（history 路由的刷新也已处理，不会 404）。以后改了前端源码，需要重新 `cd frontend && npm run build` 才生效；开发阶段还是建议配 `run-frontend.bat` 的热更新。
