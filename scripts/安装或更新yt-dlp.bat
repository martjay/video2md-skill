@echo off
chcp 65001 >nul
title 安装或更新 yt-dlp
echo.
echo  ========================================
echo   正在安装 / 更新 视频字幕工具 yt-dlp
echo   请保持网络畅通，完成后会提示「已就绪」
echo  ========================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0video2md.py" setup
  goto :done
)

where python >nul 2>&1
if %errorlevel%==0 (
  python "%~dp0video2md.py" setup
  goto :done
)

echo [失败] 没有找到 Python。
echo 请先安装 Python 3（安装时勾选 Add python.exe to PATH）：
echo https://www.python.org/downloads/
echo.
pause
exit /b 1

:done
echo.
echo 如果上面显示「yt-dlp 已就绪」，就可以回去对 AI 说「总结视频」了。
echo.
pause
