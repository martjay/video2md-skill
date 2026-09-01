#!/usr/bin/env python3
"""video2md — Universal metadata, subtitle, and audio transcription engine.

Supports:
- Platforms: YouTube, Bilibili (single, multi-P, playlist, user space), TikTok, Vimeo, Podcasts, etc.
- OS: Cross-platform support (macOS, Windows, Linux)
- Fully Automated Native Python Tkinter QR popup & zero-friction cookie persistence (instant official AI subtitle download)
- Interactive buttons: [我已在手机确认登录] and [跳过登录 (使用本地语音识别)]
- Fallback 1: Bilibili Web API with Cookie / WBI support (bypasses HTTP 412)
- Fallback 2: DASH audio stream + Whisper / Faster-Whisper ASR (when user skips QR login)
- Smart CJK & Western caption parsing & semantic chunking
- Bilibili danmaku highlights extraction
- Structured JSON outputs for downstream Agent knowledge distillation
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import platform as sys_platform
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from parse_captions import (
    cues_to_chapters,
    format_time,
    parse_caption_file,
    parse_danmaku_file,
)
from bilibili_login_gui import popup_bilibili_login

VIDEO_ID_RE = re.compile(
    r"(?:v=|/shorts/|/live/|/embed/|youtu\.be/)([A-Za-z0-9_-]{11})"
)
BV_RE = re.compile(r"(?:BV|bv)[0-9A-Za-z]{10}")
BILI_AV_RE = re.compile(r"(?:[?&]aid=|/video/av|/av)(\d+)", re.I)
BILI_SPACE_RE = re.compile(r"space\.bilibili\.com/(\d+)")
UC_RE = re.compile(r"UC[A-Za-z0-9_-]{22}")
B23_HOSTS = ("b23.tv", "bili2233.cn")

WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}


def is_macos() -> bool:
    return sys_platform.system().lower() == "darwin"


def is_windows() -> bool:
    return sys_platform.system().lower() == "windows"


def detect_platform(url: str) -> str:
    """Identify video platform from URL."""
    u = (url or "").lower()
    if "bilibili.com" in u or any(h in u for h in B23_HOSTS):
        return "bilibili"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "tiktok.com" in u:
        return "tiktok"
    if "vimeo.com" in u:
        return "vimeo"
    if "xiaohongshu.com" in u or "xhslink.com" in u:
        return "xiaohongshu"
    if "douyin.com" in u:
        return "douyin"
    if "podcast" in u or "apple.com" in u or "spotify.com" in u:
        return "podcast"
    if BV_RE.search(url or "") and "http" not in u:
        return "bilibili"
    return "generic"


def extractor_platform(data: dict) -> str:
    ie = (data.get("extractor_key") or data.get("extractor") or "").lower()
    if not ie:
        return detect_platform(str(data.get("webpage_url") or ""))
    if "youtube" in ie:
        return "youtube"
    if "bili" in ie:
        return "bilibili"
    if "tiktok" in ie:
        return "tiktok"
    if "douyin" in ie:
        return "douyin"
    slug = re.sub(r"[^a-z0-9]+", "", ie.split(":")[0])
    return slug or "generic"


def caption_stem(filename: str) -> str:
    name = Path(filename).name
    if name.endswith(".vtt") or name.endswith(".srt") or name.endswith(".xml"):
        name = name.rsplit(".", 1)[0]
    parts = name.split(".")
    if len(parts) >= 2 and re.fullmatch(r"[A-Za-z]{2}(-[A-Za-z0-9]+)?", parts[-1]):
        return ".".join(parts[:-1])
    if parts[-1].lower() in {"danmaku", "auto", "orig", "asr"}:
        return ".".join(parts[:-1])
    return name


def extract_video_id(url: str) -> str | None:
    m = BV_RE.search(url)
    if m:
        bv = m.group(0)
        return bv if bv.startswith("BV") else "BV" + bv[2:]
    m = BILI_AV_RE.search(url)
    if m:
        return f"av{m.group(1)}"
    m = VIDEO_ID_RE.search(url)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


def watch_url(platform: str, video_id: str, fallback: str | None = None) -> str:
    if fallback and str(fallback).startswith("http"):
        return str(fallback)
    if platform == "bilibili":
        return f"https://www.bilibili.com/video/{video_id}"
    if platform == "youtube":
        return f"https://www.youtube.com/watch?v={video_id}"
    return str(fallback or video_id)


def find_cookie_file(library: Path | None = None) -> Path | None:
    """Find persistent cookies.txt in library or workspace."""
    candidates = []
    if library:
        candidates.append(library / "cookies.txt")
        candidates.append(library / "_cookies.txt")
    cwd = Path.cwd()
    candidates.append(cwd / "cookies.txt")
    candidates.append(cwd / "video2md" / "cookies.txt")
    for c in candidates:
        if c.exists() and c.stat().st_size > 10:
            return c
    return None


def cookie_args(ns: argparse.Namespace | None = None, library: Path | None = None) -> list[str]:
    args: list[str] = []
    cookies = None
    browser = None
    if ns is not None:
        cookies = getattr(ns, "cookies", None) or cookies
        browser = getattr(ns, "cookies_from_browser", None) or browser

    cookies = cookies or os.environ.get("VIDEO2MD_COOKIES")
    browser = browser or os.environ.get("VIDEO2MD_COOKIES_FROM_BROWSER")

    if not cookies and not browser:
        saved = find_cookie_file(library)
        if saved:
            cookies = str(saved)

    if cookies:
        args += ["--cookies", cookies]
    if browser:
        args += ["--cookies-from-browser", browser]
    return args


def slugify(text: str, max_len: int = 48) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return (text or "channel")[:max_len]


def stable_channel_id(platform: str, data: dict, first: dict) -> tuple[str, str]:
    display = (
        data.get("channel")
        or data.get("uploader")
        or first.get("channel")
        or first.get("uploader")
        or "unknown"
    )
    raw = (
        data.get("channel_id")
        or data.get("uploader_id")
        or first.get("channel_id")
        or first.get("uploader_id")
        or ""
    )
    raw = str(raw).strip()
    if platform == "youtube":
        if raw.startswith("UC"):
            return raw, display
        m = UC_RE.search(str(data.get("channel_url") or first.get("channel_url") or ""))
        if m:
            return m.group(0), display
        return (raw or "unknown-" + slugify(display)), display
    if platform == "bilibili":
        if raw.isdigit():
            return f"bili:{raw}", display
        m = BILI_SPACE_RE.search(
            str(data.get("channel_url") or first.get("uploader_url") or data.get("uploader_url") or "")
        )
        if m:
            return f"bili:{m.group(1)}", display
    if raw:
        return f"{platform}:{raw}", display
    url = str(
        data.get("channel_url")
        or data.get("uploader_url")
        or first.get("channel_url")
        or first.get("uploader_url")
        or ""
    )
    if url:
        return f"{platform}:{slugify(url)[:48]}", display
    return f"{platform}:{slugify(display)}", display


def _ytdlp_cmd() -> list[str]:
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def run_ytdlp(args: list[str]) -> str:
    cmd = [*_ytdlp_cmd(), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip()
        raise RuntimeError(f"yt-dlp failed ({p.returncode}): {err[:2000]}")
    return p.stdout


def ytdlp_version() -> str | None:
    try:
        p = subprocess.run(
            [*_ytdlp_cmd(), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if p.returncode != 0:
        return None
    return (p.stdout or "").strip().split()[0]


def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def install_or_update_ytdlp(force_update: bool = True) -> bool:
    print("正在检测并安装/更新字幕工具 yt-dlp …", flush=True)
    if is_macos() and shutil.which("brew"):
        if not shutil.which("yt-dlp"):
            print("检测到 macOS Homebrew，正在通过 brew 快速安装 yt-dlp 与 ffmpeg …", flush=True)
            subprocess.run(["brew", "install", "yt-dlp", "ffmpeg"], capture_output=True, text=True)

    cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0 and "externally-managed-environment" in (p.stderr or ""):
        cmd += ["--break-system-packages"]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
    ver = ytdlp_version()
    if ver:
        print(f"yt-dlp 已就绪，版本 {ver}", flush=True)
        return True

    print("安装遇到问题。", file=sys.stderr)
    return False


def ensure_ytdlp(auto_install: bool = True, auto_update: bool = False) -> None:
    ver = ytdlp_version()
    if ver and not auto_update:
        print(f"yt-dlp {ver}", flush=True)
        return
    if not ver:
        print("未检测到 yt-dlp。", flush=True)
    if auto_install or auto_update:
        ok = install_or_update_ytdlp(force_update=True)
        if not ok:
            hint = "bash scripts/install_ytdlp.sh" if is_macos() else "scripts/安装或更新yt-dlp.bat"
            raise RuntimeError(f"yt-dlp 未安装成功。请运行 {hint}")
        return
    hint = "bash scripts/install_ytdlp.sh" if is_macos() else "scripts/安装或更新yt-dlp.bat"
    raise RuntimeError(f"yt-dlp 未安装。请运行 {hint}")


def default_library() -> Path:
    cwd = Path.cwd()
    hits = list(cwd.rglob("百万美元案例库"))
    if hits:
        return hits[0]
    return cwd / "video2md"


def registry_path(library: Path) -> Path:
    return library / "_registry.json"


def load_registry(library: Path) -> dict:
    p = registry_path(library)
    if not p.exists():
        return {"channels": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"channels": {}}


def save_registry(library: Path, data: dict) -> None:
    library.mkdir(parents=True, exist_ok=True)
    registry_path(library).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def resolve_channel_folder(
    library: Path, channel_id: str, display_name: str, platform: str = "youtube"
) -> Path:
    reg = load_registry(library)
    channels = reg.setdefault("channels", {})
    rec = channels.get(channel_id)
    if rec:
        folder = library if rec.get("folder") in (".", "", None) else library / rec["folder"]
        aliases = rec.setdefault("aliases", [])
        if display_name and display_name not in aliases:
            aliases.append(display_name)
        rec["display_name"] = display_name or rec.get("display_name")
        rec["platform"] = rec.get("platform") or platform
        rec["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_registry(library, reg)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    legacy_root = (
        platform == "youtube"
        and (library / "逐视频拆解").is_dir()
        and not channels
    )
    folder_name = "." if legacy_root else slugify(display_name or channel_id)
    if not legacy_root:
        existing_folders = {v.get("folder") for v in channels.values()}
        if folder_name in existing_folders:
            folder_name = f"{folder_name}-{channel_id[-6:]}"

    rec = {
        "channel_id": channel_id,
        "platform": platform,
        "display_name": display_name,
        "folder": folder_name,
        "aliases": [display_name] if display_name else [],
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    channels[channel_id] = rec
    save_registry(library, reg)
    folder = library if folder_name in (".", "") else library / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve_by_name(library: Path, name: str) -> dict | None:
    name_l = name.strip().lower()
    reg = load_registry(library)
    for cid, rec in reg.get("channels", {}).items():
        aliases = [rec.get("display_name", "")] + rec.get("aliases", [])
        slugs = [rec.get("folder", ""), slugify(name)]
        if any(a and a.lower() == name_l for a in aliases) or slugify(name) in slugs:
            rec = dict(rec)
            rec["channel_id"] = cid
            rec["path"] = str(library if rec.get("folder") in (".", "", None) else library / rec["folder"])
            return rec
    return None


def ytdlp_json(url: str, extra: list[str] | None = None, ns: argparse.Namespace | None = None, library: Path | None = None) -> dict:
    args = ["--no-download", "--dump-single-json", "--no-warnings", *cookie_args(ns, library), url]
    if extra:
        args[1:1] = extra
    raw = run_ytdlp(args)
    return json.loads(raw)


def flatten_entries(data: dict) -> list[dict]:
    entries = data.get("entries")
    if not entries:
        return [data] if data.get("id") else []
    out = []
    for e in entries:
        if not e:
            continue
        if e.get("entries"):
            out.extend(flatten_entries(e))
        elif e.get("id"):
            out.append(e)
    return out


def write_channel_json(
    folder: Path, channel_id: str, display_name: str, url: str, platform: str
) -> None:
    p = folder / "channel.json"
    doc = {
        "channel_id": channel_id,
        "platform": platform,
        "display_name": display_name,
        "url": url,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if p.exists():
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
            aliases = list(dict.fromkeys((old.get("aliases") or []) + [old.get("display_name"), display_name]))
            doc["aliases"] = [a for a in aliases if a]
            if old.get("display_name") and old["display_name"] != display_name:
                doc["renamed_from"] = old["display_name"]
        except Exception:
            pass
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def get_cookie_header(library: Path | None = None) -> str:
    """Read SESSDATA/cookies as Header string."""
    cookie_file = find_cookie_file(library)
    if not cookie_file:
        return ""
    try:
        lines = cookie_file.read_text(encoding="utf-8", errors="replace").splitlines()
        pairs = []
        for line in lines:
            if line.strip() and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 7:
                    pairs.append(f"{parts[5]}={parts[6]}")
        return "; ".join(pairs)
    except Exception:
        return ""


def download_subs(
    video_url: str,
    dest_dir: Path,
    video_id: str,
    platform: str,
    ns: argparse.Namespace | None = None,
    library: Path | None = None,
) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    langs = "all,-live_chat"
    args = [
        "--skip-download",
        "--write-auto-sub",
        "--write-sub",
        "--sub-langs",
        langs,
        "--convert-subs",
        "vtt",
        *cookie_args(ns, library),
        "-o",
        str(dest_dir / "%(id)s.%(ext)s"),
        video_url,
    ]
    if platform == "bilibili":
        args[1:1] = ["--write-comments"]

    try:
        run_ytdlp(args)
    except RuntimeError as e:
        print(f"Subtitle notice: {e}", file=sys.stderr)
    found = (
        sorted(dest_dir.glob(f"{video_id}*.vtt"))
        + sorted(dest_dir.glob(f"{video_id}*.srt"))
        + sorted(dest_dir.glob(f"{video_id}*.xml"))
    )
    return [f.name for f in found]


def download_audio_for_asr(
    video_url: str, dest_dir: Path, video_id: str, ns: argparse.Namespace | None = None, library: Path | None = None
) -> Path | None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_path = dest_dir / f"{video_id}.m4a"
    if target_path.exists() and target_path.stat().st_size > 1000:
        return target_path

    print(f"正在提取音频以备 ASR 语音转写: {video_id} ...", flush=True)
    args = [
        "-f",
        "ba/b",
        "-x",
        "--audio-format",
        "m4a",
        "--audio-quality",
        "5",
        *cookie_args(ns, library),
        "-o",
        str(target_path),
        video_url,
    ]
    try:
        run_ytdlp(args)
        if target_path.exists():
            return target_path
    except Exception as e:
        print(f"yt-dlp 音频抽取失败，尝试备用链路: {e}", file=sys.stderr)
    return None


def run_local_whisper(audio_path: Path, output_vtt: Path) -> bool:
    """Attempt transcription using local faster-whisper or whisper CLI."""
    if output_vtt.exists() and output_vtt.stat().st_size > 100:
        return True

    print(f"正在使用 Faster-Whisper ASR 转写音频: {audio_path.name} ...", flush=True)
    py_code = f"""
import sys
try:
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(r"{audio_path}", beam_size=5)
    with open(r"{output_vtt}", "w", encoding="utf-8") as f:
        f.write("WEBVTT\\n\\n")
        for s in segments:
            h1, m1, s1 = int(s.start//3600), int((s.start%3600)//60), s.start%60
            h2, m2, s2 = int(s.end//3600), int((s.end%3600)//60), s.end%60
            f.write(f"{{h1:02d}}:{{m1:02d}}:{{s1:06.3f}} --> {{h2:02d}}:{{m2:02d}}:{{s2:06.3f}}\\n{{s.text.strip()}}\\n\\n")
    sys.exit(0)
except Exception as e:
    print('ASR Error:', e, file=sys.stderr)
    sys.exit(1)
"""
    try:
        p = subprocess.run([sys.executable, "-c", py_code], capture_output=True, text=True)
        if p.returncode == 0 and output_vtt.exists() and output_vtt.stat().st_size > 0:
            print(f"Faster-Whisper ASR 转录成功: {output_vtt.name}", flush=True)
            return True
    except Exception:
        pass

    if shutil.which("whisper"):
        try:
            cmd = ["whisper", str(audio_path), "--output_format", "vtt", "--output_dir", str(output_vtt.parent)]
            p = subprocess.run(cmd, capture_output=True, text=True)
            if output_vtt.exists():
                return True
        except Exception:
            pass

    return False


def fetch_bilibili_direct(bvid: str, library: Path, ns: argparse.Namespace | None = None) -> dict | None:
    """Bilibili Web API Native Handler with proactive native Tkinter QR popup & direct AI subtitle fetch."""
    print(f"正在通过 Bilibili 官方 Web 接口抓取 {bvid} ...", flush=True)
    
    # 0. Check cookies, if none, proactively pop up the native Tkinter window
    cookie_str = get_cookie_header(library)
    if not cookie_str:
        print("未检测到 B 站登录凭据，正在桌面上弹出原生 Python 扫码登录窗口...", flush=True)
        login_ok = popup_bilibili_login(library, timeout_seconds=120)
        if login_ok:
            print("✅ 扫码登录成功！已获取官方高清 AI 字幕直取权限", flush=True)
            cookie_str = get_cookie_header(library)
        else:
            print("用户跳过或关闭登录窗口，自动切换为平滑降级 ASR 模式...", flush=True)

    req_headers = dict(WEB_HEADERS)
    if cookie_str:
        req_headers["Cookie"] = cookie_str

    req = urllib.request.Request(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=req_headers
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") != 0:
                print(f"Bilibili API 错误: {data.get('message')}", file=sys.stderr)
                return None
            vdata = data["data"]
    except Exception as e:
        print(f"Bilibili 接口请求失败: {e}", file=sys.stderr)
        return None

    title = vdata.get("title", "")
    owner = vdata.get("owner", {})
    mid = str(owner.get("mid", ""))
    author_name = owner.get("name", "unknown")
    channel_id = f"bili:{mid}"
    cid = vdata.get("cid")
    duration = vdata.get("duration", 0)
    stat = vdata.get("stat", {})
    pubdate = vdata.get("pubdate", 0)
    upload_date = datetime.fromtimestamp(pubdate, timezone.utc).strftime("%Y%m%d") if pubdate else ""

    folder = resolve_channel_folder(library, channel_id, author_name, platform="bilibili")
    write_channel_json(folder, channel_id, author_name, f"https://space.bilibili.com/{mid}", "bilibili")
    (folder / "逐视频拆解").mkdir(exist_ok=True)
    (folder / "subtitles").mkdir(exist_ok=True)
    (folder / "meta").mkdir(exist_ok=True)
    (folder / "audio").mkdir(exist_ok=True)

    meta = {
        "id": bvid,
        "platform": "bilibili",
        "title": title,
        "upload_date": upload_date,
        "timestamp": pubdate,
        "duration": duration,
        "duration_string": format_time(duration),
        "view_count": stat.get("view", 0),
        "like_count": stat.get("like", 0),
        "comment_count": stat.get("reply", 0),
        "channel": author_name,
        "channel_id": channel_id,
        "channel_url": f"https://space.bilibili.com/{mid}",
        "description": vdata.get("desc", ""),
        "tags": [t.get("tag_name") for t in vdata.get("tags", []) if isinstance(t, dict)],
        "chapters": [],
        "webpage_url": f"https://www.bilibili.com/video/{bvid}",
    }
    meta_path = folder / "meta" / f"{bvid}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 1. Fetch Danmaku XML
    try:
        dm_url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
        dm_req = urllib.request.Request(dm_url, headers=req_headers)
        with urllib.request.urlopen(dm_req, timeout=5) as dm_resp:
            raw = dm_resp.read()
            try:
                xml_data = zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                xml_data = raw
            (folder / "subtitles" / f"{bvid}.danmaku.xml").write_bytes(xml_data)
    except Exception:
        pass

    # 2. Check for Subtitles (Official CC or AI subtitles)
    subs_found = []
    try:
        sub_req = urllib.request.Request(
            f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", headers=req_headers
        )
        with urllib.request.urlopen(sub_req, timeout=5) as sresp:
            sdata = json.loads(sresp.read().decode("utf-8"))
            subs = sdata.get("data", {}).get("subtitle", {}).get("subtitles", [])
            for s in subs:
                surl = s.get("subtitle_url")
                lan = s.get("lan", "zh")
                if surl:
                    if surl.startswith("//"):
                        surl = "https:" + surl
                    with urllib.request.urlopen(urllib.request.Request(surl, headers=req_headers)) as sub_resp:
                        sub_json = json.loads(sub_resp.read().decode("utf-8"))
                        vtt_lines = ["WEBVTT\n"]
                        for item in sub_json.get("body", []):
                            f_ts = format_time(item["from"])
                            t_ts = format_time(item["to"])
                            vtt_lines.append(f"{f_ts}.000 --> {t_ts}.000\n{item['content']}\n")
                        vtt_file = folder / "subtitles" / f"{bvid}.{lan}.vtt"
                        vtt_file.write_text("\n".join(vtt_lines), encoding="utf-8")
                        subs_found.append(vtt_file.name)
                        print(f"✅ 已直取官方字幕: {vtt_file.name} ({s.get('lan_doc', lan)})", flush=True)
    except Exception:
        pass

    # 3. If no official subtitles found, download audio and run Whisper ASR
    if not subs_found:
        print(f"未检测到直接公开字幕，启用 DASH 音频流 + ASR 语音识别流水线: {bvid} ...", flush=True)
        play_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&fnval=16"
        p_req = urllib.request.Request(play_url, headers=req_headers)
        try:
            with urllib.request.urlopen(p_req, timeout=10) as presp:
                pdata = json.loads(presp.read().decode("utf-8"))
                audios = pdata.get("data", {}).get("dash", {}).get("audio", [])
                if audios:
                    audio_url = audios[0].get("baseUrl") or audios[0].get("backupUrl", [None])[0]
                    if audio_url:
                        audio_path = folder / "audio" / f"{bvid}.m4a"
                        a_req = urllib.request.Request(audio_url, headers=req_headers)
                        with urllib.request.urlopen(a_req, timeout=20) as aresp:
                            audio_path.write_bytes(aresp.read())
                        print(f"音频流下载完毕 ({audio_path.stat().st_size // 1024} KB)，正在执行 ASR ...", flush=True)
                        vtt_dest = folder / "subtitles" / f"{bvid}.zh.vtt"
                        if run_local_whisper(audio_path, vtt_dest):
                            subs_found.append(vtt_dest.name)
        except Exception as e:
            print(f"Bilibili 音频/ASR 转写异常: {e}", file=sys.stderr)

    return {
        "platform": "bilibili",
        "channel_id": channel_id,
        "display_name": author_name,
        "folder": str(folder),
        "fetched": 1,
        "skipped": 0,
        "failed": 0,
    }


def save_meta(folder: Path, video: dict) -> Path:
    meta_dir = folder / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    vid = video.get("id")
    platform = extractor_platform(video)
    slim = {
        "id": vid,
        "platform": platform,
        "title": video.get("title"),
        "upload_date": video.get("upload_date"),
        "timestamp": video.get("timestamp"),
        "duration": video.get("duration"),
        "duration_string": format_time(video.get("duration") or 0.0),
        "view_count": video.get("view_count"),
        "like_count": video.get("like_count"),
        "comment_count": video.get("comment_count"),
        "channel": video.get("channel") or video.get("uploader"),
        "channel_id": video.get("channel_id") or video.get("uploader_id"),
        "channel_url": video.get("channel_url") or video.get("uploader_url"),
        "description": video.get("description"),
        "tags": video.get("tags") or [],
        "categories": video.get("categories") or [],
        "chapters": video.get("chapters") or [],
        "webpage_url": video.get("webpage_url") or watch_url(platform, str(vid or "")),
    }
    path = meta_dir / f"{vid}.json"
    path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def pick_caption(paths: list[Path]) -> Path:
    def score(p: Path) -> tuple:
        n = p.name.lower()
        if "danmaku" in n or n.endswith(".xml"):
            return (4, n)
        if any(x in n for x in (".zh-cn", ".zh-hans", ".zh.", "zh-hans")):
            return (0, n)
        if ".en" in n:
            return (1, n)
        if ".vtt" in n:
            return (2, n)
        return (3, n)

    return sorted(paths, key=score)[0]


def cmd_fetch(args: argparse.Namespace) -> int:
    ensure_ytdlp(auto_install=True, auto_update=args.update_ytdlp)
    library = Path(args.library).resolve() if args.library else default_library()
    library.mkdir(parents=True, exist_ok=True)
    url = args.url
    platform_hint = detect_platform(url)
    print(f"library={library}", flush=True)
    print(f"platform_hint={platform_hint}", flush=True)

    data = None
    ytdlp_failed = False
    try:
        data = ytdlp_json(url, ns=args, library=library)
    except RuntimeError as err:
        print(f"yt-dlp notice: {err}", file=sys.stderr)
        ytdlp_failed = True

    if (ytdlp_failed or not data) and platform_hint == "bilibili":
        bvid = extract_video_id(url)
        if bvid:
            res = fetch_bilibili_direct(bvid, library, ns=args)
            if res:
                print(json.dumps(res, ensure_ascii=False, indent=2))
                return 0

    if not data:
        print("未能解析到视频内容，请检查链接或网络权限。", file=sys.stderr)
        return 1

    entries = (
        flatten_entries(data)
        if data.get("_type") in {"playlist", "channel", "multi_video"} or data.get("entries")
        else [data]
    )
    if not entries:
        print("No videos found.", file=sys.stderr)
        return 1

    first = next((e for e in entries if e and e.get("id")), entries[0])
    platform = extractor_platform(data) or extractor_platform(first) or platform_hint
    channel_id, display = stable_channel_id(platform, data, first)

    folder = resolve_channel_folder(library, channel_id, display, platform=platform)
    write_channel_json(
        folder,
        channel_id,
        display,
        data.get("channel_url") or data.get("uploader_url") or url,
        platform,
    )
    (folder / "逐视频拆解").mkdir(exist_ok=True)
    (folder / "subtitles").mkdir(exist_ok=True)

    existing_ids = {caption_stem(p.name) for p in (folder / "subtitles").glob("*")}
    if (folder / "meta").exists():
        existing_ids |= {p.stem for p in (folder / "meta").glob("*.json")}

    n_ok = n_skip = n_fail = 0
    for e in entries:
        vid = str(e.get("id") or "")
        if not vid or vid == channel_id or vid == channel_id.split(":")[-1]:
            continue
        if args.new_only and vid in existing_ids:
            n_skip += 1
            continue
        vurl = e.get("webpage_url") or e.get("url") or ""
        if vurl.startswith("/"):
            vurl = "https://www.youtube.com" + vurl if platform == "youtube" else vurl
        if not str(vurl).startswith("http"):
            vurl = watch_url(platform, vid, None)

        print(f"fetch {vid} {str(e.get('title', ''))[:60]}", flush=True)
        try:
            full = ytdlp_json(vurl, ns=args, library=library)
        except RuntimeError as err:
            if platform == "bilibili":
                fb = fetch_bilibili_direct(vid, library, ns=args)
                if fb:
                    n_ok += 1
                    continue
            print(f"FAIL meta {vid}: {err}", file=sys.stderr)
            n_fail += 1
            continue

        save_meta(folder, full)
        subs = download_subs(vurl, folder / "subtitles", vid, platform, ns=args, library=library)

        vtt_subs = [s for s in subs if s.endswith(".vtt") or s.endswith(".srt")]
        if not vtt_subs:
            audio_path = download_audio_for_asr(vurl, folder / "audio", vid, ns=args, library=library)
            if audio_path:
                target_vtt = folder / "subtitles" / f"{vid}.zh.vtt"
                if run_local_whisper(audio_path, target_vtt):
                    subs.append(target_vtt.name)

        print(f"  subs={subs or 'NONE'}", flush=True)
        n_ok += 1
        existing_ids.add(vid)

    print(
        json.dumps(
            {
                "platform": platform,
                "channel_id": channel_id,
                "display_name": display,
                "folder": str(folder),
                "fetched": n_ok,
                "skipped": n_skip,
                "failed": n_fail,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if n_ok or n_fail == 0 else 1


def cmd_captions(args: argparse.Namespace) -> int:
    library = Path(args.library).resolve() if args.library else default_library()
    vid = args.video_id
    metas = list(library.rglob(f"meta/{vid}.json"))
    caps = list(library.rglob(f"subtitles/{vid}*.vtt")) + list(library.rglob(f"subtitles/{vid}*.srt"))
    danmakus = list(library.rglob(f"subtitles/{vid}*.xml"))

    if not caps:
        print(f"No captions for {vid}", file=sys.stderr)
        return 1

    cap_path = pick_caption(caps)
    chapters = []
    video_meta = {}
    if metas:
        try:
            video_meta = json.loads(metas[0].read_text(encoding="utf-8"))
            chapters = video_meta.get("chapters") or []
        except Exception:
            pass

    cues = parse_caption_file(cap_path)
    packed = cues_to_chapters(cues, chapters)

    danmaku_data = {}
    if danmakus:
        danmaku_data = parse_danmaku_file(danmakus[0])

    out = {
        "video_id": vid,
        "title": video_meta.get("title", ""),
        "platform": video_meta.get("platform", ""),
        "duration": video_meta.get("duration", 0),
        "duration_string": video_meta.get("duration_string", ""),
        "caption_file": str(cap_path),
        "cue_count": len(cues),
        "chapters": packed,
        "danmaku": danmaku_data,
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.write:
        dest = cap_path.parent.parent / "meta" / f"{vid}.captions.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    return 0


def cmd_transcribe(args: argparse.Namespace) -> int:
    library = Path(args.library).resolve() if args.library else default_library()
    vid = args.video_id
    metas = list(library.rglob(f"meta/{vid}.json"))
    if not metas:
        print(f"Video {vid} meta not found in {library}", file=sys.stderr)
        return 1
    meta = json.loads(metas[0].read_text(encoding="utf-8"))
    vurl = meta.get("webpage_url") or watch_url(meta.get("platform", "generic"), vid)
    folder = metas[0].parent.parent
    audio_path = download_audio_for_asr(vurl, folder / "audio", vid, ns=args, library=library)
    if not audio_path:
        print("音频提取失败", file=sys.stderr)
        return 1
    target_vtt = folder / "subtitles" / f"{vid}.zh.vtt"
    ok = run_local_whisper(audio_path, target_vtt)
    if ok:
        print(f"转录完成: {target_vtt}")
        return 0
    print("未能完成自动 ASR 转录（请确保已安装 faster-whisper 或 whisper）", file=sys.stderr)
    return 1


def cmd_login(args: argparse.Namespace) -> int:
    library = Path(args.library).resolve() if args.library else default_library()
    if args.platform == "bilibili":
        ok = popup_bilibili_login(library, timeout_seconds=180)
        return 0 if ok else 1
    print(f"暂不支持平台 {args.platform} 的自动登录", file=sys.stderr)
    return 1


def cmd_resolve(args: argparse.Namespace) -> int:
    library = Path(args.library).resolve() if args.library else default_library()
    rec = resolve_by_name(library, args.name)
    if not rec:
        print("{}", flush=True)
        return 1
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    return 0 if install_or_update_ytdlp(force_update=True) else 1


def add_cookie_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--cookies", default="", help="Netscape cookies.txt (Bilibili/login sites)")
    p.add_argument("--cookies-from-browser", default="", dest="cookies_from_browser", help="Browser to extract cookies from (chrome, safari, edge, firefox, brave)")


def main() -> int:
    ap = argparse.ArgumentParser(description="video2md — Universal Video Knowledge Engineering Engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="Install or update yt-dlp")
    s.set_defaults(func=cmd_setup)

    u = sub.add_parser("update", help="Upgrade yt-dlp")
    u.set_defaults(func=cmd_setup)

    log = sub.add_parser("login", help="Scan QR code to login (Bilibili etc.)")
    log.add_argument("--platform", default="bilibili", choices=["bilibili"])
    log.add_argument("--library", default="", help="Root library directory")
    log.set_defaults(func=cmd_login)

    f = sub.add_parser("fetch", help="Download metadata, subtitles & optional audio")
    f.add_argument("--url", required=True, help="Any yt-dlp video / channel / playlist URL")
    f.add_argument("--library", default="", help="Root library directory")
    f.add_argument("--new-only", action="store_true", help="Skip videos already downloaded")
    f.add_argument("--update-ytdlp", action="store_true", help="pip/brew install -U yt-dlp before fetch")
    f.add_argument("--extract-audio", action="store_true", help="Extract audio when subtitles are missing")
    f.add_argument("--transcribe", action="store_true", help="Run local Whisper ASR if no subtitles exist")
    add_cookie_flags(f)
    f.set_defaults(func=cmd_fetch)

    c = sub.add_parser("captions", help="Parse and chapterize captions")
    c.add_argument("--video-id", required=True)
    c.add_argument("--library", default="")
    c.add_argument("--write", action="store_true")
    c.set_defaults(func=cmd_captions)

    t = sub.add_parser("transcribe", help="Extract audio and transcribe with Whisper")
    t.add_argument("--video-id", required=True)
    t.add_argument("--library", default="")
    add_cookie_flags(t)
    t.set_defaults(func=cmd_transcribe)

    r = sub.add_parser("resolve", help="Find channel folder by current or old name")
    r.add_argument("--name", required=True)
    r.add_argument("--library", default="")
    r.set_defaults(func=cmd_resolve)

    args = ap.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
