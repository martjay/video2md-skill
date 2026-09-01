# 🎬 video2md-skill：全品类视频知识提炼与工业级结构化知识库引擎

> **把任意视频（Bilibili、YouTube、TikTok、播客等）转化为高认知密度、干货拉满、富含实战代码与工程 SOP 的结构化 Markdown 知识库。**

---

## 🌟 核心设计哲学与亮点特性

### 1. 🤖 零门槛全自动化（AI 全程代劳）
- **告别繁琐终端命令**：用户只需在 IDE 中发送一句 `总结视频 https://...`，AI 会自动代劳执行所有依赖检查、API 抓取、音频流下载、ASR 语音转录与文档编排；
- **通俗易懂的开局选项**：通过自然语言交互弹窗确认总结偏好（深度极客拆解、事实核验、批量加速等），绝无晦涩生硬的学术黑话。

### 2. 📱 B 站原生独立扫码登录与 0.2 秒直取
- **彻底告别 HTTP 412 风控**：内置纯 Python 原生 GUI 弹窗引擎，支持一键扫码登录；
- **永久持久化 Cookie**：扫码一次自动保存至 `video2md/cookies.txt`，永久生效；
- **秒级直取官方字幕**：优先拉取 B 站官方「中文 (AI)」与 CC 高清软字幕，零 CPU 占用，秒级完成！
- **平滑 ASR 降级保底**：当遇到 UP 主压制的硬字幕视频时，全自动提取高清 DASH 音频流并调用本地 Faster-Whisper 进行离线语音转写，双重闭环绝不中断。

### 3. 📖 纯粹极客的人类友好型文档排版
- **彻底去除冗余元数据**：摒弃复杂的 YAML 机器报头与冗余 JSON 规则，直奔核心干货；
- **全景思维导图与架构图**：Mermaid 业务流程图与架构接缝一目了然；
- **真实生产级代码与测试**：提供真实可运行的 TypeScript 接口契约、Vitest 行为单测、前后对比目录树与落地 SOP；
- **双向互联知识图谱**：自动生成 `00-总索引.md`，文档间支持上下篇无缝跳转。

### 4. 🍏 跨平台全系统原生兼容
- 🪟 **Windows**：原生支持 `cmd / PowerShell / pythonw`，提供独立一键批处理；
- 🍎 **macOS**：原生适配 Homebrew (`brew install yt-dlp ffmpeg`)、Shell 脚本与系统权限；
- 🐧 **Linux**：适配 Ubuntu / Debian / Arch 等各主流发行版。

---

## 📂 知识库生成目录规范

执行总结后，知识库将按照**频道持久唯一标识**自动沉淀为如下结构：

```
video2md/
├── _registry.json                 # 全局持久化频道注册表（防止 UP 主更名丢失）
├── cookies.txt                    # B 站/第三方网站登录凭据（标准 Netscape 格式）
└── {channel_slug}/                # 频道专属知识库目录 (如: chhsich, dadafastrun)
    ├── channel.json               # 频道基础信息与主页链接
    ├── meta/                      # 原始视频元数据 JSON 档案
    │   └── {videoId}.json
    ├── subtitles/                 # 提取的高清字幕文件 (.vtt / .srt) 与弹幕 (.xml)
    │   ├── {videoId}.zh.vtt
    │   └── {videoId}.danmaku.xml
    ├── audio/                     # ASR 语音识别轻量音频缓存 (.m4a)
    │   └── {videoId}.m4a
    └── 逐视频拆解/                 # ⭐ 人类高密度深度 Markdown 知识库
        ├── 00-总索引.md            # 频道全量视频表格总目录与状态索引
        ├── 001-{videoId}-{title}.md
        ├── 002-{videoId}-{title}.md
        └── 003-{videoId}-{title}.md
```

---

## 🚀 快速上手指南

### 第一步：环境准备（仅首次需要）

确保电脑已安装 Python 3.10+。

- **Windows 用户**：双击运行 `scripts/安装或更新yt-dlp.bat`
- **macOS / Linux 用户**：终端运行 `bash scripts/安装或更新yt-dlp.sh`（或 `brew install yt-dlp ffmpeg`）

---

### 第二步：B 站扫码登录（一劳永逸，建议先运行）

为了能够秒级直取 B 站官方 AI 字幕并彻底绕过 412 风控，建议先进行一次扫码登录：

- **Windows 用户**：双击运行 `scripts/登录B站.bat`
- **macOS / Linux 用户**：终端运行 `bash scripts/登录B站.sh`
- **命令行方式**：在根目录下执行 `python scripts/bilibili_login_gui.py`

#### 📱 登录弹窗特性：
1. 屏幕中央立即弹出小巧精致的 **220×220px 二维码窗口**；
2. 打开手机 **「哔哩哔哩 App」** 扫码并点击确认；
3. 窗口会自动捕获登录成功并自动关闭，凭据永久保存至 `video2md/cookies.txt`！
4. 窗口底部配备 **【✅ 我已在手机确认登录】** 与 **【⏭️ 跳过登录】** 按钮。

---

### 第三步：日常使用（直接在 AI 聊天中对话）

在 Cursor / Antigravity / Claude Code 中，直接对 AI 说：

```text
总结视频 https://www.bilibili.com/video/BV1mubY6jE4u
```

或者：

```text
拆解这个频道的所有视频 https://space.bilibili.com/588699709
```

AI 会自动弹出交互选项供您确认，并在后台自动完成抓取、去重、代码提炼与总索引更新！

---

## 🛠️ CLI 核心命令进阶速查（供开发者）

所有底层操作均可通过 `scripts/video2md.py` 驱动：

```bash
# 1. 抓取单个视频（自动使用 cookies.txt，优先软字幕，缺失自动 ASR）
python scripts/video2md.py fetch --url "https://www.bilibili.com/video/BV1zUh56RE8k" --library ./video2md

# 2. 全频道/空间增量抓取（自动跳过本地已存在的视频）
python scripts/video2md.py fetch --url "https://space.bilibili.com/588699709" --library ./video2md --new-only

# 3. 解析字幕并输出带时间戳的章节结构
python scripts/video2md.py captions --video-id BV1zUh56RE8k --library ./video2md --write

# 4. 单独对某视频音频进行 Faster-Whisper 本地转录
python scripts/video2md.py transcribe --video-id BV1zUh56RE8k --library ./video2md
```

---

## ❓ 常见问题排查与 FAQ

### Q1：抓取 B 站视频提示 `HTTP Error 412: Precondition Failed` 是为什么？
- **解答**：这是 B 站针对未登录高频爬虫的风控限制。运行一次 `scripts/登录B站.bat` 或 `scripts/登录B站.sh` 完成扫码登录后，生成 `video2md/cookies.txt` 即可永久解决。

### Q2：为什么有些视频 0.5 秒就解析完了，有些视频需要 20~30 秒？
- **解答**：
  - **0.5 秒完成**：该视频在 B 站自带官方「中文 (AI)」或 CC 字幕，脚本通过 Cookie 极速直取字幕文本；
  - **20~30 秒完成**：该视频为 UP 主压制的硬字幕视频（服务器上无独立文本字幕），脚本自动启用了本地 `Faster-Whisper` ASR 语音模型进行离线听写转录。

### Q3：换了新电脑或 Cookie 过期了怎么办？
- **解答**：随时重新双击 `scripts/登录B站.bat` 或 `scripts/登录B站.sh`，重新扫码 5 秒钟即可刷新凭据。

---

## 📜 开源协议

MIT License. 欢迎提交 PR 与 Issue！
