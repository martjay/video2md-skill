# 支持的平台与跨平台站点指南

`video2md-skill` 基于 **yt-dlp 与官方原生 API 双引擎** 构建，支持全球 1000+ 视频与播客站点，并在 **macOS**、**Windows**、**Linux** 上实现全平台兼容。

---

## 常见平台链接与主键映射

| 平台 | 单视频链接示例 | 频道/合集/空间链接示例 | 稳定主键 (Channel Key) |
| :--- | :--- | :--- | :--- |
| **YouTube** | `https://www.youtube.com/watch?v=...`<br>`https://youtu.be/...` | `@handle`<br>`https://www.youtube.com/channel/UC...` | `UC...` (24位稳定 ID) |
| **Bilibili** | `https://www.bilibili.com/video/BV...`<br>`?p=1,2,3...` (多P) | `https://space.bilibili.com/{mid}`<br>合集/系列列表链接 | `bili:{mid}` (数字 UID) |
| **TikTok / 抖音** | 网页分享短链或完整 URL | 用户主页 URL | `tiktok:{user_id}` / `douyin:{sec_uid}` |
| **小红书** | `https://www.xiaohongshu.com/explore/...` | 用户主页 | `xiaohongshu:{user_id}` |
| **播客 (Podcasts)** | Apple Podcasts / Spotify / 独立 RSS 音频链接 | 播客专栏主页 | `podcast:{feed_id}` |
| **通用音视频** | Vimeo, Twitter/X, Dailymotion, Coursera 等 | 播放列表或课程主页 | `{platform}:{uploader_id}` |

---

## 登录态与权限处理 (B 站扫码登录 & Cookie 方案)

### 🥇 方案 1：B 站一键扫码登录（最推荐 · 0.2 秒直取官方 AI 字幕）
直接在终端或对话中执行：
```bash
python scripts/video2md.py login --platform bilibili
```
- 系统会自动弹出登录二维码图片窗口；
- 使用哔哩哔哩手机 App 扫码并在手机上点击确认；
- Cookie 会自动保存至 `video2md/cookies.txt`；
- **后续所有抓取自动生效，免除本地 Whisper CPU 消耗，秒级直取官方「中文 (AI)」字幕！**

---

### 🥈 方案 2：从本地浏览器直接读取 Cookie
- **macOS**：
  ```bash
  python scripts/video2md.py fetch --url "..." --cookies-from-browser safari
  # 或 chrome, edge, brave, firefox
  ```
- **Windows / Linux**：
  ```bash
  python scripts/video2md.py fetch --url "..." --cookies-from-browser chrome
  # 或 edge, firefox
  ```

---

## 音视频处理与 ASR 降级

若原视频确实无任何官方或 AI 字幕：
1. 自动启用 DASH 音频抽取与 Faster-Whisper ASR 语音识别；
2. 依赖建议：
   - **macOS**：通过 `brew install ffmpeg yt-dlp` 安装；
   - **Windows**：已内置 ffmpeg；
   - **Linux**：`sudo apt install ffmpeg`。
