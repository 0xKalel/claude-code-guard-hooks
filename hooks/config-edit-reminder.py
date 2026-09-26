#!/usr/bin/env python3
"""PostToolUse reminder: editing config/*.php requires a horizon restart.

Queued jobs keep the stale config until `docker compose restart horizon`
(prod: `sudo systemctl restart ravenclip-horizon`). Emits additionalContext
so the reminder lands in Claude's context, not as an error.
"""

import json
import re
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if re.search(r"/config/[^/]+\.php$", file_path):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"Reminder: {file_path} is a config file — queued jobs keep the stale "
                    "config until `docker compose restart horizon` "
                    "(prod: `sudo systemctl restart ravenclip-horizon`)."
                ),
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
