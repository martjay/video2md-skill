#!/usr/bin/env python3
"""Native Python Tkinter GUI Dialog for Bilibili QR Code Login.
Zero external app dependency. Pops up directly on top of the user's desktop with
interactive buttons: [我已在手机确认登录] and [跳过登录 (使用本地语音识别)].
"""
from __future__ import annotations

import http.cookiejar
import io
import json
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    import qrcode
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}


def center_window(root: tk.Tk, width: int = 380, height: int = 500) -> None:
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")


class BilibiliLoginDialog:
    def __init__(self, library_dir: Path, timeout_seconds: int = 120):
        self.library_dir = library_dir
        self.timeout_seconds = timeout_seconds
        self.login_success = False
        self.is_running = True
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

        self.qr_key: Optional[str] = None
        self.qr_url: Optional[str] = None
        self.tk_img: Optional[ImageTk.PhotoImage] = None

        self.root: Optional[tk.Tk] = None
        self.status_label: Optional[tk.Label] = None
        self.qr_label: Optional[tk.Label] = None

    def fetch_qr_code(self) -> bool:
        gen_url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        req = urllib.request.Request(gen_url, headers=WEB_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))["data"]
                self.qr_url = data["url"]
                self.qr_key = data["qrcode_key"]
                return True
        except Exception:
            return False

    def render_qr_image(self, size: int = 220) -> Optional[ImageTk.PhotoImage]:
        if not self.qr_url:
            return None
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(self.qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert("RGBA")
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def save_cookies(self) -> None:
        self.library_dir.mkdir(parents=True, exist_ok=True)
        cookie_file = self.library_dir / "cookies.txt"
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for c in self.cookie_jar:
                domain = c.domain if c.domain.startswith(".") else "." + c.domain
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = c.path
                secure = "TRUE" if c.secure else "FALSE"
                expires = str(c.expires or int(time.time() + 86400 * 30))
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{c.name}\t{c.value}\n")

    def poll_loop(self) -> None:
        start_time = time.time()
        while self.is_running and (time.time() - start_time < self.timeout_seconds):
            time.sleep(1.5)
            if not self.is_running or not self.qr_key:
                break
            poll_url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.qr_key}"
            try:
                p_req = urllib.request.Request(poll_url, headers=WEB_HEADERS)
                with self.opener.open(p_req, timeout=5) as p_resp:
                    p_data = json.loads(p_resp.read().decode("utf-8"))
                    code = p_data.get("data", {}).get("code")
                    if code == 0:
                        self.login_success = True
                        self.save_cookies()
                        self.update_status("🎉 登录成功！正在进入极速直取通道...", "#22c55e")
                        time.sleep(0.8)
                        self.close_window()
                        break
                    elif code == 86090:
                        self.update_status("📱 已扫码，请在手机上点击「确认登录」", "#38bdf8")
                    elif code == 86038:
                        self.update_status("⚠️ 二维码已失效，正在刷新...", "#f59e0b")
                        if self.fetch_qr_code():
                            self.tk_img = self.render_qr_image()
                            if self.root and self.qr_label:
                                self.root.after(0, lambda: self.qr_label.config(image=self.tk_img))
            except Exception:
                pass

        if not self.login_success and self.is_running:
            self.close_window()

    def update_status(self, text: str, color: str = "#94a3b8") -> None:
        if self.root and self.status_label:
            try:
                self.root.after(0, lambda: self.status_label.config(text=text, fg=color))
            except Exception:
                pass

    def on_confirm_clicked(self) -> None:
        """User clicks 'I have confirmed on mobile'."""
        self.update_status("🔍 正在校验登录状态...", "#38bdf8")
        if not self.qr_key:
            return
        poll_url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.qr_key}"
        try:
            p_req = urllib.request.Request(poll_url, headers=WEB_HEADERS)
            with self.opener.open(p_req, timeout=5) as p_resp:
                p_data = json.loads(p_resp.read().decode("utf-8"))
                code = p_data.get("data", {}).get("code")
                if code == 0:
                    self.login_success = True
                    self.save_cookies()
                    self.update_status("🎉 登录成功！", "#22c55e")
                    self.root.after(500, self.close_window)
                elif code == 86090:
                    self.update_status("📱 手机端还未点击「确认登录」，请在手机上确认", "#f59e0b")
                else:
                    self.update_status("⏳ 尚未检测到扫码，请使用 B 站 App 扫码", "#94a3b8")
        except Exception as e:
            self.update_status(f"校验异常: {e}", "#ef4444")

    def on_skip_clicked(self) -> None:
        """User clicks 'Skip login'."""
        self.login_success = False
        self.close_window()

    def close_window(self) -> None:
        self.is_running = False
        if self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass

    def enforce_topmost(self) -> None:
        """Keep window on top and focused on Windows/macOS/Linux."""
        if self.root and self.is_running:
            try:
                self.root.attributes("-topmost", True)
                self.root.lift()
                self.root.after(500, self.enforce_topmost)
            except Exception:
                pass

    def show(self) -> bool:
        if not TK_AVAILABLE:
            return False

        if not self.fetch_qr_code():
            return False

        self.root = tk.Tk()
        self.root.title("哔哩哔哩扫码登录")
        self.root.configure(bg="#0f172a")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_skip_clicked)
        center_window(self.root, width=380, height=520)

        # Title container
        title_frame = tk.Frame(self.root, bg="#0f172a", pady=10)
        title_frame.pack(fill="x")

        main_title = tk.Label(
            title_frame,
            text="📱 Bilibili 扫码登录",
            font=("Segoe UI", 16, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        )
        main_title.pack()

        sub_title = tk.Label(
            title_frame,
            text="扫码登录可直接秒级获取官方 AI 高清字幕",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#0f172a",
        )
        sub_title.pack(pady=3)

        # QR Code Container
        qr_card = tk.Frame(self.root, bg="#ffffff", padx=12, pady=12, relief="flat")
        qr_card.pack(pady=10)

        self.tk_img = self.render_qr_image(size=220)
        self.qr_label = tk.Label(qr_card, image=self.tk_img, bg="#ffffff")
        self.qr_label.pack()

        # Status text
        self.status_label = tk.Label(
            self.root,
            text="👉 请打开手机「哔哩哔哩 App」扫码并确认",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#0f172a",
            wraplength=340,
        )
        self.status_label.pack(pady=8)

        # Buttons Frame
        btn_frame = tk.Frame(self.root, bg="#0f172a", pady=8)
        btn_frame.pack(fill="x", padx=30)

        confirm_btn = tk.Button(
            btn_frame,
            text="✅ 我已在手机确认登录",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            command=self.on_confirm_clicked,
        )
        confirm_btn.pack(fill="x", pady=4)

        skip_btn = tk.Button(
            btn_frame,
            text="⏭️ 跳过登录（使用本地语音识别转写）",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#cbd5e1",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=5,
            command=self.on_skip_clicked,
        )
        skip_btn.pack(fill="x", pady=4)

        # Start background polling thread & topmost enforcement
        t = threading.Thread(target=self.poll_loop, daemon=True)
        t.start()
        self.enforce_topmost()

        # Focus window
        try:
            self.root.focus_force()
        except Exception:
            pass

        try:
            self.root.mainloop()
        except Exception:
            pass

        return self.login_success


def popup_bilibili_login(library_dir: Path, timeout_seconds: int = 120) -> bool:
    """Public helper to pop up the native Tkinter Bilibili login dialog."""
    dialog = BilibiliLoginDialog(library_dir, timeout_seconds=timeout_seconds)
    return dialog.show()


if __name__ == "__main__":
    import sys
    dest = Path(__file__).resolve().parent.parent / "video2md"
    ok = popup_bilibili_login(dest)
    print("Login result:", ok)
    sys.exit(0 if ok else 1)
