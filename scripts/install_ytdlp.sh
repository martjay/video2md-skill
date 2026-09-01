#!/usr/bin/env bash
# ==============================================================================
# 安装或更新 yt-dlp 与音视频工具 (macOS & Linux 专用脚本)
# ==============================================================================

set -e

echo "========================================"
echo " 正在为 macOS / Linux 配置 video2md 环境"
echo "========================================"
echo ""

# 1. macOS Homebrew 优先检测
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "检测到系统为 macOS..."
  if command -v brew >/dev/null 2>&1; then
    echo "使用 Homebrew 安装/更新 yt-dlp 和 ffmpeg..."
    brew install yt-dlp ffmpeg || true
    echo "Homebrew 依赖配置完成！"
  fi
fi

# 2. Python 环境与 pip 安装
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  python3 "$SCRIPT_DIR/video2md.py" setup
elif command -v python >/dev/null 2>&1; then
  python "$SCRIPT_DIR/video2md.py" setup
else
  echo "[错误] 未检测到 Python 3 环境。"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS 用户可通过以下命令安装 Python 和 yt-dlp："
    echo "brew install python yt-dlp ffmpeg"
  else
    echo "Linux 用户可通过包管理器安装："
    echo "sudo apt update && sudo apt install python3 python3-pip yt-dlp ffmpeg"
  fi
  exit 1
fi

echo ""
echo "========================================"
echo " 环境准备就绪！现在可以回到 AI 对话发送「总结视频」了。"
echo "========================================"
