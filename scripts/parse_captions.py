"""parse_captions.py — Robust multilingual caption parser, deduplicator, and chunker.

Features:
1. Dual-mode deduplication:
   - Word-level N-gram deduplication for spaced languages (English, French, etc.)
   - Character-level sliding-window & substring deduplication for CJK (Chinese, Japanese, Korean)
2. Overlap and rolling auto-caption artifact cleaning
3. Intelligent auto-chunking when official chapters are missing (5-12 min semantic time splits)
4. Bilibili XML/Protobuf danmaku and live-chat highlights parser
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def is_cjk(text: str) -> bool:
    """Detect if text contains significant Chinese, Japanese, or Korean characters."""
    if not text:
        return False
    cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    return cjk_count / max(len(text.strip()), 1) > 0.2


def parse_time(ts: str) -> float:
    """Parse timestamp string (HH:MM:SS.mmm or MM:SS.mmm) into seconds."""
    ts = ts.replace(",", ".").split()[0]
    p = ts.split(":")
    try:
        if len(p) == 3:
            h, m, s = p
            return int(h) * 3600 + int(m) * 60 + float(s)
        if len(p) == 2:
            m, s = p
            return int(m) * 60 + float(s)
        return float(p[0])
    except (ValueError, IndexError):
        return 0.0


def format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS string."""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _dedupe_cjk(text: str) -> str:
    """Deduplicate rolling auto-subtitles for CJK (no-space) text.

    Uses character sliding window matching and contiguous phrase deduplication.
    """
    text = re.sub(r"\s+", "", text)
    if not text:
        return ""

    # 1. Remove consecutive identical substrings (length 2 to 30)
    changed = True
    while changed:
        changed = False
        n = len(text)
        for length in range(min(30, n // 2), 1, -1):
            pattern = re.compile(rf"(.{{{length}}})\1+")
            new_text = pattern.sub(r"\1", text)
            if new_text != text:
                text = new_text
                changed = True
                break

    return text


def _dedupe_words(text: str) -> str:
    """Deduplicate rolling auto-subtitles for space-delimited languages."""
    prev = ""
    cur = text
    while cur != prev:
        prev = cur
        words = cur.split()
        if not words:
            return ""
        out: list[str] = []
        for w in words:
            out.append(w)
            n = len(out)
            for k in range(n // 2, 0, -1):
                if n >= 2 * k and out[-2 * k : -k] == out[-k:]:
                    out = out[:-k]
                    break
        cur = " ".join(out)
    return cur


def dedupe_caption(text: str) -> str:
    """Language-aware caption deduplication."""
    if not text:
        return ""
    text = text.strip()
    if is_cjk(text):
        return _dedupe_cjk(text)
    return _dedupe_words(text)


def _clean_line(line: str) -> str:
    """Clean subtitle tags, HTML entities, and sound effects."""
    line = re.sub(r"<[^>]+>", "", line)  # HTML/VTT tags
    line = re.sub(r"\{[^\}]+\}", "", line)  # ASS style tags
    line = line.replace("&gt;&gt;", ">>").replace("&amp;", "&").replace("&nbsp;", " ")
    line = line.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    # Filter common auto-subtitle sound descriptions
    line = re.sub(r"\[(?:music|applause|laughter|silence|singing|cheering|sound)\]", "", line, flags=re.I)
    line = re.sub(r"\((?:music|applause|laughter|silence|singing|cheering|sound)\)", "", line, flags=re.I)
    line = re.sub(r"【(?:音乐|掌声|笑声|欢呼|背景音)】", "", line)
    return line.strip()


def parse_caption_file(path: Path) -> list[tuple[float, str]]:
    """Parse VTT/SRT file into normalized (start_time, text) cues with rolling deduplication."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    raw_cues: list[tuple[float, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            parts = line.split("-->")
            start = parse_time(parts[0].strip())
            i += 1
            content_parts: list[str] = []
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                c = _clean_line(lines[i])
                if c and not c.isdigit():
                    content_parts.append(c)
                i += 1
            if content_parts:
                joined = " ".join(content_parts) if not is_cjk("".join(content_parts)) else "".join(content_parts)
                cleaned = dedupe_caption(joined)
                if cleaned:
                    raw_cues.append((start, cleaned))
        else:
            i += 1

    # Merge consecutive identical cues and remove rolling overlap
    merged: list[tuple[float, str]] = []
    for t, c in raw_cues:
        if not merged:
            merged.append((t, c))
            continue
        prev_t, prev_c = merged[-1]
        if prev_c == c:
            continue
        # Check if current cue is a complete prefix/suffix of previous cue
        if is_cjk(c) and is_cjk(prev_c):
            if c.startswith(prev_c):
                merged[-1] = (prev_t, c)
                continue
            if prev_c.endswith(c):
                continue
            # Longest common overlap check
            min_overlap = min(len(prev_c), len(c), 15)
            overlap_found = False
            for ol in range(min_overlap, 3, -1):
                if prev_c.endswith(c[:ol]):
                    combined = prev_c + c[ol:]
                    merged[-1] = (prev_t, _dedupe_cjk(combined))
                    overlap_found = True
                    break
            if overlap_found:
                continue
        merged.append((t, c))

    return merged


def auto_generate_chapters(
    cues: list[tuple[float, str]], target_chunk_seconds: float = 480.0
) -> list[dict]:
    """Generate balanced semantic chapters when video lacks official chapter metadata.

    Target chunk length: ~8 minutes (480s), aligned to natural subtitle pauses.
    """
    if not cues:
        return []
    total_duration = cues[-1][0]
    if total_duration <= target_chunk_seconds * 1.3:
        # Short video: single unified chapter
        text = "".join(c for _, c in cues) if is_cjk(cues[0][1]) else " ".join(c for _, c in cues)
        return [{
            "title": "全片核心内容拆解 (Full Content)",
            "start": 0.0,
            "end": total_duration,
            "cue_count": len(cues),
            "text": text,
        }]

    num_chunks = max(2, math.ceil(total_duration / target_chunk_seconds))
    approx_chunk_len = total_duration / num_chunks

    chapters: list[dict] = []
    current_cues: list[str] = []
    chunk_start = 0.0
    current_chunk_idx = 1

    for idx, (t, c) in enumerate(cues):
        current_cues.append(c)
        time_elapsed = t - chunk_start
        is_last = idx == len(cues) - 1

        should_split = (
            not is_last
            and time_elapsed >= approx_chunk_len * 0.85
            and (time_elapsed >= approx_chunk_len * 1.15 or (idx + 1 < len(cues) and cues[idx + 1][0] - t > 3.0))
        )

        if should_split or is_last:
            joined = "".join(current_cues) if current_cues and is_cjk(current_cues[0]) else " ".join(current_cues)
            chunk_end = t if not is_last else total_duration
            chapters.append({
                "title": f"第 {current_chunk_idx} 部分 ({format_time(chunk_start)} - {format_time(chunk_end)})",
                "start": chunk_start,
                "end": chunk_end,
                "cue_count": len(current_cues),
                "text": dedupe_caption(joined),
            })
            current_cues = []
            chunk_start = cues[idx + 1][0] if idx + 1 < len(cues) else total_duration
            current_chunk_idx += 1

    return chapters


def cues_to_chapters(
    cues: list[tuple[float, str]],
    chapters: list[dict],
) -> list[dict]:
    """Align subtitle cues with official video chapters, or auto-chunk if none exist."""
    if not cues:
        return []

    if not chapters:
        return auto_generate_chapters(cues)

    out = []
    for i, ch in enumerate(chapters):
        start = float(ch.get("start_time") or 0)
        end = float(chapters[i + 1]["start_time"]) if i + 1 < len(chapters) else 1e12
        parts = [c for t, c in cues if start <= t < end]
        joined = "".join(parts) if parts and is_cjk(parts[0]) else " ".join(parts)
        out.append({
            "title": ch.get("title") or f"Chapter {i+1}",
            "start": start,
            "end": None if end > 1e11 else end,
            "cue_count": len(parts),
            "text": dedupe_caption(joined),
        })
    return out


def parse_danmaku_file(path: Path) -> dict:
    """Parse Bilibili XML / JSON danmaku to extract high-energy time clusters & notes."""
    if not path.exists():
        return {"total_count": 0, "hot_spots": [], "highlights": []}

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"total_count": 0, "hot_spots": [], "highlights": []}

    danmakus: list[tuple[float, str]] = []

    # XML Format (Bilibili standard)
    if "<i" in content and "</d>" in content:
        try:
            root = ET.fromstring(content)
            for d in root.findall("d"):
                p_attr = d.get("p", "")
                text = (d.text or "").strip()
                if p_attr and text:
                    sec = float(p_attr.split(",")[0])
                    danmakus.append((sec, text))
        except Exception:
            pass

    if not danmakus:
        return {"total_count": 0, "hot_spots": [], "highlights": []}

    # Filter knowledge/high-value notes (e.g. timestamps, explanations, formulas, corrections)
    valuable_keywords = [
        "课代表", "总结", "时间戳", "传送门", "注意", "重点", "核心", "原理",
        "补充", "纠错", "勘误", "公式", "代码", "github", "链接", "翻译", "出处"
    ]
    curated_notes = []
    for sec, text in danmakus:
        if any(kw in text.lower() for kw in valuable_keywords) and len(text) >= 4:
            curated_notes.append({"time": format_time(sec), "seconds": sec, "text": text})

    # Cluster high-energy moments (30-second windows)
    bucket_size = 30
    buckets: dict[int, int] = {}
    for sec, _ in danmakus:
        b = int(sec // bucket_size)
        buckets[b] = buckets.get(b, 0) + 1

    sorted_buckets = sorted(buckets.items(), key=lambda x: x[1], reverse=True)[:5]
    hot_spots = [
        {
            "start": format_time(b * bucket_size),
            "end": format_time((b + 1) * bucket_size),
            "density": count,
        }
        for b, count in sorted_buckets if count >= 10
    ]

    return {
        "total_count": len(danmakus),
        "hot_spots": hot_spots,
        "highlights": curated_notes[:15],
    }
