import json
import subprocess
import winreg
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from tools.registry import tool

MIC_CONSENT = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"


def _endpoint_volume(device):
    if hasattr(device, "EndpointVolume"):
        return device.EndpointVolume
    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def _get_default_mic():
    mic = AudioUtilities.GetMicrophone()
    if mic is None:
        return None, None
    return mic, _endpoint_volume(mic)


def _get_default_speakers():
    speakers = AudioUtilities.GetSpeakers()
    if speakers is None:
        return None, None
    return speakers, _endpoint_volume(speakers)


def _device_name(device):
    name = getattr(device, "FriendlyName", None)
    if name:
        return name
    try:
        dev_id = device.GetId()
        for d in AudioUtilities.GetAllDevices():
            if d.id == dev_id:
                return d.FriendlyName
    except Exception:
        pass
    return "unknown"


def _status(device, vol):
    return {
        "name": _device_name(device),
        "muted": bool(vol.GetMute()),
        "volume_percent": round(vol.GetMasterVolumeLevelScalar() * 100),
    }


def _apply(vol, muted, volume_percent):
    if muted is not None:
        vol.SetMute(1 if muted else 0, None)
    if volume_percent is not None:
        level = max(0, min(100, int(volume_percent)))
        vol.SetMasterVolumeLevelScalar(level / 100, None)


def _read_consent(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, "Value")
            return value
    except OSError:
        return "unknown"


def _audio_endpoints():
    cmd = "Get-PnpDevice -Class AudioEndpoint | Select-Object FriendlyName, Status | ConvertTo-Json"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    return data


@tool(
    description=(
        "Diagnose microphone problems. Returns all audio devices and their status, "
        "the default microphone with mute and volume, and Windows microphone privacy settings. "
        "Desktop apps like Zoom, Teams and Discord need desktop_apps_access to be Allow."
    )
)
def check_microphone():
    info = {"audio_devices": _audio_endpoints()}

    mic, vol = _get_default_mic()
    info["default_microphone"] = _status(mic, vol) if vol else "No default microphone found"

    info["privacy"] = {
        "microphone_access": _read_consent(MIC_CONSENT),
        "desktop_apps_access": _read_consent(MIC_CONSENT + r"\NonPackaged"),
    }
    return info


@tool(
    description=(
        "Mute or unmute the default MICROPHONE (input) and or set its recording volume from 0 to 100. "
        "This is not the speaker volume."
    ),
    parameters={
        "type": "object",
        "properties": {
            "muted": {"type": "boolean", "description": "true to mute, false to unmute."},
            "volume_percent": {"type": "integer", "description": "Microphone volume from 0 to 100."},
        },
    },
    risk="low",
)
def set_microphone(muted=None, volume_percent=None):
    mic, vol = _get_default_mic()
    if vol is None:
        return "No default microphone found."
    _apply(vol, muted, volume_percent)
    return _status(mic, vol)


@tool(description="Get the default SPEAKERS (output) name, mute status and volume. This is the system volume the user hears.")
def check_speakers():
    speakers, vol = _get_default_speakers()
    if vol is None:
        return "No default speakers found."
    return _status(speakers, vol)


@tool(
    description=(
        "Mute or unmute the default SPEAKERS (output) and or set the system volume from 0 to 100. "
        "Use this when the user talks about laptop volume, sound or speaker volume."
    ),
    parameters={
        "type": "object",
        "properties": {
            "muted": {"type": "boolean", "description": "true to mute, false to unmute."},
            "volume_percent": {"type": "integer", "description": "Speaker volume from 0 to 100."},
        },
    },
    risk="low",
)
def set_speakers(muted=None, volume_percent=None):
    speakers, vol = _get_default_speakers()
    if vol is None:
        return "No default speakers found."
    _apply(vol, muted, volume_percent)
    return _status(speakers, vol)


@tool(
    description="Allow apps and desktop apps like Zoom to access the microphone in Windows privacy settings.",
    risk="change",
)
def allow_microphone_access():
    for path in (MIC_CONSENT, MIC_CONSENT + r"\NonPackaged"):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "Value", 0, winreg.REG_SZ, "Allow")
    return "Microphone access allowed for apps and desktop apps. Restart Zoom if it is open."