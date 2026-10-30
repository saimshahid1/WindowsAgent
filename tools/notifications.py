import winreg
from tools.registry import tool

NOTIF_PATH = r"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings"


@tool(
    description=(
        "List apps registered for Windows notifications with their app_id and whether "
        "notifications are enabled. Use search to filter by name, for example 'linkedin' or 'chrome'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "search": {
                "type": "string",
                "description": "Optional text to filter app IDs.",
            },
        },
    },
)
def list_notification_apps(search=""):
    apps = []
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, NOTIF_PATH) as key:
        i = 0
        while True:
            try:
                app_id = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1

            if search and search.lower() not in app_id.lower():
                continue

            enabled = True
            try:
                with winreg.OpenKey(key, app_id) as sub:
                    value, _ = winreg.QueryValueEx(sub, "Enabled")
                    enabled = value != 0
            except OSError:
                pass

            apps.append({"app_id": app_id, "enabled": enabled})

    if not apps:
        return "No matching apps found."
    return apps


@tool(
    description=(
        "Turn Windows notifications on or off for one app. "
        "Always call list_notification_apps first to get the exact app_id."
    ),
    parameters={
        "type": "object",
        "properties": {
            "app_id": {
                "type": "string",
                "description": "Exact app_id from list_notification_apps.",
            },
            "enabled": {
                "type": "boolean",
                "description": "true to turn notifications on, false to turn them off.",
            },
        },
        "required": ["app_id", "enabled"],
    },
    risk="change",
)
def set_app_notifications(app_id, enabled):
    full_path = NOTIF_PATH + "\\" + app_id
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, full_path).Close()
    except OSError:
        return f"App {app_id} not found. Use list_notification_apps to get the exact app_id."

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, full_path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Enabled", 0, winreg.REG_DWORD, 1 if enabled else 0)

    state = "on" if enabled else "off"
    return f"Notifications for {app_id} turned {state}."