def PrettyPrint(msg, type="info"): # Inspired by FortnitePorting
    reset = u"\u001b[0m"
    color = reset
    match type.lower():
        case "info":
            color = u"\u001b[36m"
        case "warn" | "warning":
            color = u"\u001b[33m"
        case "error":
            color = u"\u001b[31m"
        case _:
            pass
    print(f"{color}[HD2SDK:CE]{reset} {msg}")