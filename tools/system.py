import platform
import psutil
from tools.registry import tool


@tool(description="Get basic system information like OS, CPU usage, RAM, disk space and battery.")
def get_system_info():
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    battery = psutil.sensors_battery()

    info = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu_usage_percent": psutil.cpu_percent(interval=1),
        "cpu_cores": psutil.cpu_count(),
        "ram_total_gb": round(ram.total / 1024**3, 1),
        "ram_used_percent": ram.percent,
        "disk_c_total_gb": round(disk.total / 1024**3, 1),
        "disk_c_free_gb": round(disk.free / 1024**3, 1),
    }

    if battery:
        info["battery_percent"] = battery.percent
        info["charging"] = battery.power_plugged

    return info