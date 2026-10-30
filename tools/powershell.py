import subprocess
from tools.registry import tool


@tool(
    description=(
        "Run a Windows PowerShell command on the user's computer and return the output. "
        "Use this for any task that no other tool can do. "
        "Prefer read only commands to check things first before changing anything."
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The PowerShell command to run.",
            },
            "reason": {
                "type": "string",
                "description": "Short explanation for the user of what this command does and why.",
            },
        },
        "required": ["command", "reason"],
    },
    risk="change",
)
def run_powershell(command, reason=""):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )

    output = result.stdout.strip()
    error = result.stderr.strip()

    if error:
        output += f"\nERROR\n{error}"
    if not output:
        output = "Command ran successfully with no output."

    return output[:4000]