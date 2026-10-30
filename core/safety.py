import re
from tools.registry import TOOLS

SAFE_VERBS = {
    "get", "select", "sort", "where", "format", "measure",
    "test", "group", "compare", "resolve", "foreach", "out", "convertto",
}

DANGEROUS_PATTERNS = [
    r">",
    r"&",
    r"\biex\b",
    r"\binvoke-",
    r"\bout-file\b",
    r"-encodedcommand",
    r"\b(rm|del|erase|rd|rmdir|kill|taskkill|shutdown|reg|sc|net|netsh|wmic|diskpart|bcdedit)\b",
    r"\.(kill|delete|stop|start|terminate|setvalue|create)\s*\(",
]


def is_read_only_powershell(command):
    cmd = command.lower()

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            return False

    if "::" in cmd.replace("[math]::", ""):
        return False

    verbs = re.findall(r"\b([a-z]+)-[a-z]+\b", cmd)
    if not verbs:
        return False

    return all(v in SAFE_VERBS for v in verbs)


def needs_confirmation(name, args):
    t = TOOLS.get(name)
    if t is None or t["risk"] == "read":
        return False
    if name == "run_powershell" and is_read_only_powershell(args.get("command", "")):
        return False
    return True


def ask_user(name, args):
    print(f"\n  Agent wants to run {name}")
    if "reason" in args:
        print(f"  Reason  {args['reason']}")
    if "command" in args:
        print(f"  Command {args['command']}")
    else:
        print(f"  Args    {args}")

    answer = input("  Allow? (y/n) ").strip().lower()
    return answer in ("y", "yes")