TOOLS = {}


def tool(description, parameters=None, risk="read"):
    def decorator(func):
        TOOLS[func.__name__] = {
            "function": func,
            "risk": risk,
            "schema": {
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": description,
                    "parameters": parameters or {"type": "object", "properties": {}},
                },
            },
        }
        return func
    return decorator


def get_schemas():
    return [t["schema"] for t in TOOLS.values()]


def run_tool(name, args):
    if name not in TOOLS:
        return f"Error, unknown tool {name}"
    try:
        result = TOOLS[name]["function"](**args)
        return str(result)
    except Exception as e:
        return f"Error, {e}"