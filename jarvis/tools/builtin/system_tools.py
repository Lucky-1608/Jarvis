"""
Jarvis OS — Built-in System Tools.

Core tools for interacting with the operating system:
  - open_app:      Launch an application
  - run_command:   Execute a shell command
  - system_info:   Get CPU, RAM, disk info
  - list_files:    List directory contents
  - read_file:     Read a file
  - write_file:    Write/create a file
  - search_files:  Search for files by name
  - get_datetime:  Get current date/time
"""

from __future__ import annotations

import asyncio
import datetime
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import structlog

from jarvis.tools.base import (
    Tool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------
class SystemInfoTool(Tool):
    """Retrieve system information (CPU, RAM, disk, OS)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="system_info",
            description="Get current system information including CPU, RAM, disk usage, and OS details.",
            category=ToolCategory.SYSTEM,
        )

    async def execute(self, **params: Any) -> ToolResult:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu": {
                    "cores_physical": psutil.cpu_count(logical=False),
                    "cores_logical": psutil.cpu_count(logical=True),
                    "usage_percent": cpu_percent,
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round(disk.percent, 1),
                },
                "uptime_hours": round((
                    datetime.datetime.now().timestamp() - psutil.boot_time()
                ) / 3600, 1),
            }
            return ToolResult(success=True, output=info)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Open Application
# ---------------------------------------------------------------------------
class OpenAppTool(Tool):
    """Launch a desktop application."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="open_app",
            description="Open/launch a desktop application by name, optionally navigating to a URL if it is a browser.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="app_name",
                    type="string",
                    description="Name of the application to open (e.g., 'chrome', 'firefox', 'brave', 'edge'). If no app is specified but you want to open a website, set this to the URL.",
                ),
                ToolParameter(
                    name="target_url",
                    type="string",
                    description="(Optional) The URL to open within the application, if the app is a web browser.",
                ),
            ],
        )

    # Common app name → command mappings (Windows)
    _APP_MAP_WINDOWS = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "edge browser": "msedge.exe",
        "ms edge": "msedge.exe",
        "brave": "brave.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "windows terminal": "wt.exe",
        "vscode": "code.cmd",
        "vs code": "code.cmd",
        "visual studio code": "code.cmd",
        "task manager": "taskmgr.exe",
        "paint": "mspaint.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "spotify": "spotify.exe",
    }

    @staticmethod
    def _find_app_shortcut(app_name: str) -> str | None:
        if sys.platform != "win32":
            return None
            
        import os
        from pathlib import Path
        
        def clean_name(name: str) -> str:
            return "".join(c for c in name.lower() if c.isalnum())
            
        app_name_clean = clean_name(app_name)
        if not app_name_clean:
            return None
            
        start_menu_paths = [
            Path(os.environ.get("ProgramData", "C:\\ProgramData")) / "Microsoft\\Windows\\Start Menu\\Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft\\Windows\\Start Menu\\Programs",
            Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop",
            Path(os.environ.get("USERPROFILE", "")) / "Desktop",
        ]

        for menu_path in start_menu_paths:
            if not menu_path.exists():
                continue
            for p in menu_path.rglob("*.lnk"):
                if clean_name(p.stem) == app_name_clean:
                    return str(p)

        for menu_path in start_menu_paths:
            if not menu_path.exists():
                continue
            for p in menu_path.rglob("*.lnk"):
                if app_name_clean in clean_name(p.stem):
                    return str(p)
                    
        return None
    _WEBSITE_MAP = {
        # E-commerce & Shopping (India Focus)
        "amazon": "https://www.amazon.in",
        "flipkart": "https://www.flipkart.com",
        "myntra": "https://www.myntra.com",
        "meesho": "https://www.meesho.com",
        "nykaa": "https://www.nykaa.com",
        "ajio": "https://www.ajio.com",
        "snapdeal": "https://www.snapdeal.com",
        "firstcry": "https://www.firstcry.com",
        "lenskart": "https://www.lenskart.com",
        "purplle": "https://www.purplle.com",
        "croma": "https://www.croma.com",
        "reliancedigital": "https://www.reliancedigital.in",
        "jiomart": "https://www.jiomart.com",
        "tataneu": "https://www.tatadigital.com",
        
        # Quick Commerce & Food Delivery (India)
        "blinkit": "https://blinkit.com",
        "zepto": "https://www.zeptonow.com",
        "bigbasket": "https://www.bigbasket.com",
        "swiggy": "https://www.swiggy.com",
        "zomato": "https://www.zomato.com",
        
        # Pharmacies & Health (India)
        "pharmeasy": "https://pharmeasy.in",
        "1mg": "https://www.1mg.com",
        "netmeds": "https://www.netmeds.com",
        "apollo": "https://www.apollopharmacy.in",
        
        # Travel, Tickets & Utilities (India)
        "makemytrip": "https://www.makemytrip.com",
        "cleartrip": "https://www.cleartrip.com",
        "goibibo": "https://www.goibibo.com",
        "yatra": "https://www.yatra.com",
        "irctc": "https://www.irctc.co.in",
        "bookmyshow": "https://in.bookmyshow.com",
        "ola": "https://www.olacabs.com",
        "uber": "https://www.uber.com/in/en/",
        "urbancompany": "https://www.urbancompany.com",
        
        # Global E-commerce
        "ebay": "https://www.ebay.com",
        "walmart": "https://www.walmart.com",
        "target": "https://www.target.com",
        "bestbuy": "https://www.bestbuy.com",
        "etsy": "https://www.etsy.com",
        "aliexpress": "https://www.aliexpress.com",
        "alibaba": "https://www.alibaba.com",
        "temu": "https://www.temu.com",
        "shein": "https://www.shein.com",
        "wayfair": "https://www.wayfair.com",
        "costco": "https://www.costco.com",
        "ikea": "https://www.ikea.com",
        "shopify": "https://www.shopify.com",
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://github.com",
        "netflix": "https://www.netflix.com",
        "gmail": "https://mail.google.com",
        "twitter": "https://twitter.com",
        "x": "https://twitter.com",
        "reddit": "https://www.reddit.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "linkedin": "https://www.linkedin.com",
        "whatsapp": "https://web.whatsapp.com",
        
        # Social Media & Messaging
        "tiktok": "https://www.tiktok.com",
        "snapchat": "https://www.snapchat.com",
        "pinterest": "https://www.pinterest.com",
        "discord": "https://discord.com/app",
        "telegram": "https://web.telegram.org",
        "twitch": "https://www.twitch.tv",
        "threads": "https://www.threads.net",
        "bluesky": "https://bsky.app",
        "mastodon": "https://joinmastodon.org",
        "tumblr": "https://www.tumblr.com",
        "wechat": "https://web.wechat.com",
        "viber": "https://www.viber.com",
        "line": "https://line.me",
        "signal": "https://signal.org",
        
        # AI Tools & Platforms
        "chatgpt": "https://chatgpt.com",
        "claude": "https://claude.ai",
        "perplexity": "https://www.perplexity.ai",
        "gemini": "https://gemini.google.com",
        "huggingface": "https://huggingface.co",
        "midjourney": "https://www.midjourney.com",
        "poe": "https://poe.com",
        "characterai": "https://character.ai",
        "runway": "https://runwayml.com",
        "mistral": "https://chat.mistral.ai",
        "v0": "https://v0.dev",
        "cursor": "https://cursor.com",
        "replicate": "https://replicate.com",
        "anthropic": "https://www.anthropic.com",
        "openai": "https://openai.com",
        "grok": "https://x.com/i/grok",
        "civitai": "https://civitai.com",
        "elevenlabs": "https://elevenlabs.io",
        "suno": "https://suno.com",
        "udio": "https://www.udio.com",
        
        # Google Apps / Workspace
        "drive": "https://drive.google.com",
        "googledrive": "https://drive.google.com",
        "docs": "https://docs.google.com/document",
        "googledocs": "https://docs.google.com/document",
        "sheets": "https://docs.google.com/spreadsheets",
        "googlesheets": "https://docs.google.com/spreadsheets",
        "slides": "https://docs.google.com/presentation",
        "googleslides": "https://docs.google.com/presentation",
        "forms": "https://docs.google.com/forms",
        "googleforms": "https://docs.google.com/forms",
        "maps": "https://maps.google.com",
        "googlemaps": "https://maps.google.com",
        "photos": "https://photos.google.com",
        "googlephotos": "https://photos.google.com",
        "calendar": "https://calendar.google.com",
        "googlecalendar": "https://calendar.google.com",
        "meet": "https://meet.google.com",
        "googlemeet": "https://meet.google.com",
        "contacts": "https://contacts.google.com",
        "googlecontacts": "https://contacts.google.com",
        "translate": "https://translate.google.com",
        "googletranslate": "https://translate.google.com",
        "keep": "https://keep.google.com",
        "googlekeep": "https://keep.google.com",
        "earth": "https://earth.google.com",
        "googleearth": "https://earth.google.com",
        "news": "https://news.google.com",
        "googlenews": "https://news.google.com",
        
        # Streaming Platforms
        "hotstar": "https://www.hotstar.com",
        "primevideo": "https://www.primevideo.com",
        "zee5": "https://www.zee5.com",
        "sonyliv": "https://www.sonyliv.com",
        "jiocinema": "https://www.jiocinema.com",
        "disneyplus": "https://www.disneyplus.com",
        "crunchyroll": "https://www.crunchyroll.com",
        "appletv": "https://tv.apple.com",
        "viki": "https://www.viki.com",
        "discoveryplus": "https://www.discoveryplus.com",
        "mxplayer": "https://www.mxplayer.in",
        "aha": "https://www.aha.video",
        "sunnxt": "https://www.sunnxt.com",
        "altbalaji": "https://www.altt.co.in",
        "erosnow": "https://erosnow.com",
        "mubi": "https://mubi.com",
        "hoichoi": "https://www.hoichoi.tv",
        "lionsgateplay": "https://lionsgateplay.com",
        "shemaroome": "https://www.shemaroome.com",
        "hungama": "https://www.hungama.com",
        "epicon": "https://www.epicon.in",
        "manoramamax": "https://www.manoramamax.com",
        "chaupal": "https://www.chaupal.tv",
        "ullu": "https://ullu.app",
    }

    async def execute(self, **params: Any) -> ToolResult:
        app_name = params.get("app_name", "").strip().lower()
        target_url = params.get("target_url", "").strip()
        
        if not app_name:
            return ToolResult(success=False, error="No application name provided.")

        try:
            if app_name in self._WEBSITE_MAP:
                app_name = self._WEBSITE_MAP[app_name]

            if platform.system() == "Windows":
                # Handle URLs provided directly in app_name
                if "." in app_name and " " not in app_name and not app_name.startswith("http"):
                    app_name = f"https://{app_name}"
                    
                cmd_exe = self._APP_MAP_WINDOWS.get(app_name)
                
                if cmd_exe:
                    try:
                        if target_url:
                            os.startfile(cmd_exe, arguments=target_url)
                        else:
                            os.startfile(cmd_exe)
                    except Exception as e:
                        return ToolResult(success=False, error=f"Failed to open '{cmd_exe}': {e}")
                else:
                    if app_name.startswith("http"):
                        os.startfile(app_name)
                    else:
                        shortcut = self._find_app_shortcut(app_name)
                        if shortcut:
                            if target_url:
                                os.startfile(shortcut, "open", target_url)
                            else:
                                os.startfile(shortcut)
                        else:
                            app_name_clean = "".join(c for c in app_name.lower() if c.isalnum())
                            ps_cmd = f"Get-StartApps | Where-Object {{ ($_.Name -replace '[^a-zA-Z0-9]', '') -match '{app_name_clean}' }} | Select-Object -ExpandProperty AppID"
                            proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, creationflags=0x08000000)
                            app_ids = [line.strip() for line in proc.stdout.strip().split("\n") if line.strip()]
                            
                            if app_ids:
                                subprocess.Popen(f'explorer.exe shell:AppsFolder\\{app_ids[0]}', shell=True)
                            else:
                                try:
                                    if target_url:
                                        os.startfile(app_name, arguments=target_url)
                                    else:
                                        os.startfile(app_name)
                                except OSError:
                                    return ToolResult(success=False, error=f"Could not find or open application '{app_name}'.")
            elif platform.system() == "Darwin":
                if app_name.startswith("http"):
                    subprocess.Popen(["open", app_name])
                else:
                    subprocess.Popen(["open", "-a", app_name])
            else:  # Linux
                if app_name.startswith("http"):
                    subprocess.Popen(f"xdg-open {app_name} &", shell=True)
                else:
                    subprocess.Popen(f"{app_name} &", shell=True)

            return ToolResult(
                success=True,
                output=f"Launched '{app_name}' successfully.",
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"Failed to open '{app_name}': {exc}")


# ---------------------------------------------------------------------------
# Close Application
# ---------------------------------------------------------------------------
class CloseAppTool(Tool):
    """Close/kill a desktop application."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="close_app",
            description="Close a desktop application by name, or close the current active app/window when app_name is 'current', 'active', or 'this app'.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="app_name",
                    type="string",
                    description="Name of the application to close, or 'current'/'active'/'this app' to close the foreground window.",
                ),
            ],
        )

    _CLOSE_MAP_WINDOWS = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "brave": "brave.exe",
        "notepad": "notepad.exe",
        "calculator": "CalculatorApp.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "vscode": "Code.exe",
        "vs code": "Code.exe",
        "visual studio code": "Code.exe",
        "task manager": "Taskmgr.exe",
        "spotify": "Spotify.exe",
        "word": "WINWORD.EXE",
        "microsoft word": "WINWORD.EXE",
        "excel": "EXCEL.EXE",
        "microsoft excel": "EXCEL.EXE",
        "powerpoint": "POWERPNT.EXE",
        "microsoft powerpoint": "POWERPNT.EXE",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "terminal": "WindowsTerminal.exe",
        "windows terminal": "WindowsTerminal.exe",
    }

    _CURRENT_WINDOW_ALIASES = {
        "active",
        "active app",
        "active application",
        "active window",
        "any",
        "any app",
        "any application",
        "any window",
        "app",
        "application",
        "current",
        "current app",
        "current application",
        "current window",
        "foreground",
        "foreground app",
        "foreground window",
        "this",
        "this app",
        "this application",
        "this window",
        "the app",
        "the application",
        "the window",
        "that app",
        "opened app",
        "open app",
        "window",
    }

    _WINDOW_ONLY_APPS = {"explorer", "file explorer"}

    async def execute(self, **params: Any) -> ToolResult:
        raw_app_name = params.get("app_name", "")
        app_name = self._normalize_app_name(str(raw_app_name))
        if not app_name:
            return ToolResult(success=False, error="No application name provided.")

        try:
            if platform.system() == "Windows":
                if app_name in self._CURRENT_WINDOW_ALIASES:
                    closed = self._close_active_window()
                    if closed:
                        return ToolResult(success=True, output=closed)

                    hotkey_result = self._send_alt_f4()
                    if hotkey_result:
                        return ToolResult(success=True, output=hotkey_result)

                    return ToolResult(
                        success=False,
                        error="Could not close the active window. Install pygetwindow or pyautogui for active-window control.",
                    )

                window_result = self._close_matching_window(app_name)
                if window_result:
                    return ToolResult(success=True, output=window_result)

                if app_name in self._WINDOW_ONLY_APPS:
                    return ToolResult(
                        success=True,
                        output=f"No File Explorer window matching '{app_name}' was open.",
                    )

                process_names = self._resolve_windows_process_names(app_name)

                for process_name in process_names:
                    result = await self._taskkill(process_name)
                    if result.success:
                        return result

                psutil_result = self._terminate_matching_processes(app_name, process_names)
                if psutil_result:
                    if "Failed to terminate: Access Denied" in psutil_result:
                        return ToolResult(success=False, error=psutil_result)
                    return ToolResult(success=True, output=psutil_result)

                tried = ", ".join(process_names)
                return ToolResult(
                    success=True,
                    output=f"'{raw_app_name}' is not currently running (or was already successfully closed). Tried checking: {tried}.",
                )
            
            elif platform.system() == "Darwin":
                proc = await asyncio.create_subprocess_shell(f'killall "{app_name}"', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    return ToolResult(success=True, output=f"Closed '{app_name}' successfully.")
                return ToolResult(success=False, error=f"Failed to close '{app_name}'.")
            else:  # Linux
                proc = await asyncio.create_subprocess_shell(f'pkill -f "{app_name}"', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await proc.communicate()
                if proc.returncode == 0:
                    return ToolResult(success=True, output=f"Closed '{app_name}' successfully.")
                return ToolResult(success=False, error=f"Failed to close '{app_name}'.")

        except Exception as exc:
            return ToolResult(success=False, error=f"Error closing '{app_name}': {exc}")

    @classmethod
    def _normalize_app_name(cls, app_name: str) -> str:
        normalized = " ".join(app_name.strip().lower().split())
        for prefix in ("please close ", "close ", "quit ", "exit ", "kill ", "terminate ", "stop "):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        for suffix in (" app", " application", " browser", " window"):
            if normalized.endswith(suffix) and normalized not in cls._CURRENT_WINDOW_ALIASES:
                normalized = normalized[: -len(suffix)].strip()
        return normalized

    @classmethod
    def _resolve_windows_process_names(cls, app_name: str) -> list[str]:
        names: list[str] = []
        for key, exe in cls._CLOSE_MAP_WINDOWS.items():
            if key in app_name:
                names.append(exe)

        if not names:
            names.append(app_name if app_name.endswith(".exe") else f"{app_name}.exe")

        return list(dict.fromkeys(names))

    @staticmethod
    async def _taskkill(process_name: str) -> ToolResult:
        proc = await asyncio.create_subprocess_exec(
            "taskkill",
            "/F",
            "/IM",
            process_name,
            "/T",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        out_str = stdout.decode("utf-8", errors="replace").strip()
        err_str = stderr.decode("utf-8", errors="replace").strip()
        combined = f"{out_str}\n{err_str}".lower()

        if proc.returncode == 0 or "success:" in combined:
            return ToolResult(
                success=True,
                output=f"Closed '{process_name}' successfully. {out_str or err_str}",
            )

        if "not found" in combined or "no tasks" in combined:
            return ToolResult(success=False, error=f"'{process_name}' is not running.")

        return ToolResult(
            success=False,
            error=f"Failed to close '{process_name}'. ReturnCode: {proc.returncode} | Error: {err_str} | Output: {out_str}",
        )

    @staticmethod
    def _close_active_window() -> str | None:
        if sys.platform != "win32":
            return None

        try:
            import pygetwindow as gw
            import ctypes
            import psutil
        except ImportError:
            return None

        window = gw.getActiveWindow()
        if not window:
            return None

        title = window.title or "active window"
        hwnd = window._hWnd
        window.close()
        time.sleep(0.5)
        
        # Verify and force kill if still open
        remaining_hwnds = {w._hWnd for w in gw.getAllWindows()}
        if hwnd in remaining_hwnds:
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value > 0:
                try:
                    p = psutil.Process(pid.value)
                    p.terminate()
                    p.wait(timeout=3)
                except Exception:
                    pass

        return f"Closed active window '{title}'."

    @staticmethod
    def _close_matching_window(app_name: str) -> str | None:
        if sys.platform != "win32":
            return None

        try:
            import pygetwindow as gw
            import ctypes
            import psutil
        except ImportError:
            return None

        matches = []
        for window in gw.getAllWindows():
            title = (window.title or "").strip()
            if title and app_name in title.lower():
                matches.append(window)

        if not matches:
            return None

        closed_titles = []
        for window in matches:
            if window.isMinimized:
                window.restore()
            closed_titles.append(window.title)
            window.close()

        time.sleep(0.5)
        
        # Verify and force kill if still open
        remaining_hwnds = {w._hWnd for w in gw.getAllWindows()}
        for window in matches:
            if window._hWnd in remaining_hwnds:
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(window._hWnd, ctypes.byref(pid))
                if pid.value > 0:
                    try:
                        p = psutil.Process(pid.value)
                        p.terminate()
                        p.wait(timeout=3)
                    except Exception:
                        pass

        return f"Closed {len(closed_titles)} window(s): {', '.join(closed_titles[:5])}."

    @staticmethod
    def _send_alt_f4() -> str | None:
        try:
            import pyautogui
        except ImportError:
            return None

        pyautogui.hotkey("alt", "f4")
        time.sleep(0.5)
        return "Sent Alt+F4 to the active window."

    @staticmethod
    def _terminate_matching_processes(app_name: str, process_names: list[str]) -> str | None:
        matches: list[psutil.Process] = []
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                name = (proc.info.get("name") or "").lower()
                exe = Path(proc.info.get("exe") or "").stem.lower()
            except (psutil.Error, OSError):
                continue

            is_match = (app_name in name) or (app_name in exe)
            for p in process_names:
                p_stem = Path(p).stem.lower()
                if p_stem == name or p_stem == exe or p.lower() == name:
                    is_match = True
                    break

            if is_match:
                matches.append(proc)

        if not matches:
            return None

        terminated = []
        for proc in matches:
            try:
                terminated.append(f"{proc.name()} ({proc.pid})")
                proc.terminate()
            except psutil.Error:
                continue

        _, alive = psutil.wait_procs(matches, timeout=3)
        for proc in alive:
            try:
                proc.kill()
            except psutil.Error:
                pass

        return f"Closed matching process(es): {', '.join(terminated[:8])}."


# ---------------------------------------------------------------------------
# Run Command
# ---------------------------------------------------------------------------
class RunCommandTool(Tool):
    """Execute a shell command."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="run_command",
            description="Execute a shell/terminal command and return the output. Use with caution.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The shell command to execute.",
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory for the command.",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds (default: 30).",
                    required=False,
                    default=30,
                ),
            ],
            dangerous=True,
        )

    async def execute(self, **params: Any) -> ToolResult:
        command = params.get("command", "").strip()
        cwd = params.get("cwd")
        timeout = params.get("timeout", 30)

        if not command:
            return ToolResult(success=False, error="No command provided.")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            output = {
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip(),
            }

            return ToolResult(
                success=proc.returncode == 0,
                output=output,
                error=output["stderr"] if proc.returncode != 0 else None,
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s.")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# List Files
# ---------------------------------------------------------------------------
class ListFilesTool(Tool):
    """List contents of a directory."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="list_files",
            description="List files and directories in a given path.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory path to list.",
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Whether to list recursively.",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        path_str = params.get("path", ".").strip()
        recursive = params.get("recursive", False)

        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            return ToolResult(success=False, error=f"Path does not exist: {path}")
        if not path.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")

        try:
            entries = []
            iterator = path.rglob("*") if recursive else path.iterdir()
            for item in iterator:
                try:
                    stat = item.stat()
                    entries.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size_bytes": stat.st_size if item.is_file() else None,
                    })
                except PermissionError:
                    entries.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "unknown",
                        "error": "permission denied",
                    })
                if len(entries) >= 500:  # safety limit
                    break

            return ToolResult(
                success=True,
                output={"path": str(path), "count": len(entries), "entries": entries},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Read File
# ---------------------------------------------------------------------------
class ReadFileTool(Tool):
    """Read the contents of a text file."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read and return the contents of a text file.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read.",
                ),
                ToolParameter(
                    name="max_lines",
                    type="integer",
                    description="Maximum number of lines to read (default: 200).",
                    required=False,
                    default=200,
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        path_str = params.get("path", "").strip()
        max_lines = params.get("max_lines", 200)

        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if not path.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)

            content = "".join(lines)
            return ToolResult(
                success=True,
                output={
                    "path": str(path),
                    "lines": len(lines),
                    "truncated": len(lines) >= max_lines,
                    "content": content,
                },
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Write File
# ---------------------------------------------------------------------------
class WriteFileTool(Tool):
    """Write content to a file."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description="Write or create a file with the given content.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to write.",
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file.",
                ),
            ],
            dangerous=True,
        )

    async def execute(self, **params: Any) -> ToolResult:
        path_str = params.get("path", "").strip()
        content = params.get("content", "")

        path = Path(path_str).expanduser().resolve()

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"Written {len(content)} chars to {path}",
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Search Files
# ---------------------------------------------------------------------------
class SearchFilesTool(Tool):
    """Search for files by name pattern."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_files",
            description="Search for files matching a name pattern in a directory.",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="directory",
                    type="string",
                    description="Directory to search in.",
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern to match (e.g., '*.py', '*.txt').",
                ),
            ],
        )

    async def execute(self, **params: Any) -> ToolResult:
        directory = params.get("directory", ".").strip()
        pattern = params.get("pattern", "*").strip()

        path = Path(directory).expanduser().resolve()
        if not path.exists():
            return ToolResult(success=False, error=f"Directory not found: {path}")

        try:
            matches = []
            for item in path.rglob(pattern):
                matches.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                })
                if len(matches) >= 200:
                    break

            return ToolResult(
                success=True,
                output={"pattern": pattern, "directory": str(path), "count": len(matches), "matches": matches},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Get Date/Time
# ---------------------------------------------------------------------------
class GetDateTimeTool(Tool):
    """Get current date and time."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_datetime",
            description="Get the current date, time, and timezone.",
            category=ToolCategory.SYSTEM,
        )

    async def execute(self, **params: Any) -> ToolResult:
        now = datetime.datetime.now()
        utc = datetime.datetime.now(datetime.timezone.utc)
        return ToolResult(
            success=True,
            output={
                "local": now.isoformat(),
                "utc": utc.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day": now.strftime("%A"),
                "timezone": str(datetime.datetime.now().astimezone().tzinfo),
            },
        )


# ---------------------------------------------------------------------------
# Factory — register all built-in system tools
# ---------------------------------------------------------------------------
def get_system_tools() -> list[Tool]:
    """Return instances of all built-in system tools."""
    return [
        SystemInfoTool(),
        OpenAppTool(),
        CloseAppTool(),
        RunCommandTool(),
        ListFilesTool(),
        ReadFileTool(),
        WriteFileTool(),
        SearchFilesTool(),
        GetDateTimeTool(),
    ]
