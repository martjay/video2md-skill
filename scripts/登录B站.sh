#!/usr/bin/env bash
# ==============================================================================
# Bilibili 扫码登录启动脚本 (macOS / Linux)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "❌ 错误：未检测到 Python 环境，请先安装 Python 3。" >&2
    exit 1
fi

echo "🚀 正在启动 Bilibili 扫码登录窗口..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/bilibili_login_gui.py"
