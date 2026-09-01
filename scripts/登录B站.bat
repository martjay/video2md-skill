@echo off
chcp 65001 >nul
cd /d "%~dp0.."
start "" pythonw scripts\bilibili_login_gui.py
