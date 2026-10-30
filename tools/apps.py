import ctypes
import json
import subprocess
import time
from ctypes import wintypes

import psutil
from tools.registry import tool

PROTECTED = {
    "explorer", "csrss", "winlogon", "wininit", "services", "lsass",
    "svchost", "smss", "system", "dwm", "python", "pythonw", "powershell",
}

user32 = ctypes.windll.user32
WM_CLOSE = 0x0010
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _ps(cmd):
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )


def _normalize(name):
    name = name.lower().strip()
    return name[:-4] if name.endswith(".exe") else name


def _find_processes(process_name):
    target = _normalize(process_name)
    return [p for p in psutil.process_iter(["pid", "name"]) if _normalize(p.info["name"] or "") == target]


def _find_windows(text):
    text = text.lower().strip()
    matches = []

    def callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if text in buf.value.lower():
                    matches.append((hwnd, buf.value))
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return matches


@tool(
    description=(
        "List apps that currently have an open window, with process name, id and window title."
    )
)
def list_running_apps():
    cmd = "Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object Name, Id, MainWindowTitle | ConvertTo-Json"
    try:
        data = json.loads(_ps(cmd).stdout)
    except json.JSONDecodeError:
        return "Could not read running apps."
    if isinstance(data, dict):
        data = [data]
    return data


@tool(
    description="Open an installed app by its name, for example 'Microsoft Store', 'Notepad', 'Calculator' or 'Spotify'.",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of the app as it appears in the Start menu."},
        },
        "required": ["app_name"],
    },
    risk="low",
)
def open_app(app_name):
    safe = app_name.replace("'", "''")
    cmd = f"Get-StartApps | Where-Object {{ $_.Name -like '*{safe}*' }} | Select-Object -First 5 Name, AppID | ConvertTo-Json"
    try:
        data = json.loads(_ps(cmd).stdout)
    except json.JSONDecodeError:
        return f"No app found matching {app_name}."
    if isinstance(data, dict):
        data = [data]

    exact = [a for a in data if a["Name"].lower() == app_name.lower()]
    app = exact[0] if exact else data[0]

    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app['AppID']}"])
    return f"Opened {app['Name']}."


@tool(
    description=(
        "Close an app normally, like clicking the X button, so it can ask to save unsaved work. "
        "Give the app name or window title, for example 'Microsoft Store' or 'Notepad'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "App name, window title or process name."},
        },
        "required": ["app_name"],
    },
    risk="low",
)
def close_app(app_name):
    if _normalize(app_name) in PROTECTED:
        return f"{app_name} is a protected system process and will not be closed."

    windows = _find_windows(app_name)
    if windows:
        for hwnd, _ in windows:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        time.sleep(2)
        if not _find_windows(app_name):
            titles = ", ".join(t for _, t in windows)
            return f"Closed {titles}."
        return f"{app_name} is still open. It may be asking the user to save. Tell the user to check it."

    procs = _find_processes(app_name)
    if not procs:
        return f"No open window or process found for {app_name}."

    pids = ",".join(str(p.pid) for p in procs)
    _ps(f"Get-Process -Id {pids} -ErrorAction SilentlyContinue | ForEach-Object {{ $_.CloseMainWindow() | Out-Null }}")
    time.sleep(2)
    if not [p for p in procs if p.is_running()]:
        return f"{app_name} closed."
    return f"{app_name} did not close normally. force_close_app can close it but unsaved work will be lost."


@tool(
    description="Force close an app immediately by process name. Unsaved work will be lost. Only use if close_app did not work.",
    parameters={
        "type": "object",
        "properties": {
            "process_name": {"type": "string", "description": "Exact process name of the app."},
        },
        "required": ["process_name"],
    },
    risk="change",
)
def force_close_app(process_name):
    if _normalize(process_name) in PROTECTED:
        return f"{process_name} is a protected system process and will not be closed."

    procs = _find_processes(process_name)
    if not procs:
        return f"No running process named {process_name}."

    for p in procs:
        try:
            p.kill()
        except psutil.Error:
            pass
    return f"{process_name} force closed."