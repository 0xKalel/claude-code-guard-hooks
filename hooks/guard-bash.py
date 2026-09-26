#!/usr/bin/env python3
"""PreToolUse guard for Bash commands (wired in .claude/settings.json).

Blocks the three command classes that CLAUDE.md forbids but nothing enforced:
  1. Destructive migrations (dev DB `autonews` holds REAL data).
  2. `config:cache` aimed at production (breaks env()-read key pools → silent no-story).
  3. Bare `php artisan` / pint / pest on the host (there is no local PHP; must run
     inside the `app` container). Prod commands over ssh legitimately run native
     artisan, so ssh lines are exempt from this rule only.

Exit 2 + stderr = block the call and show the message to Claude.
"""

import json
import re
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0

    if re.search(r"migrate:fresh|migrate:refresh|migrate:reset|db:wipe", command) \
            and "DB_ALLOW_DESTRUCTIVE=true" not in command:
        print(
            "BLOCKED: destructive migration command. The default connection is the dev DB "
            "`autonews` (REAL data). Use plain `docker compose exec -T app php artisan migrate` "
            "for new migrations, or `bash scripts/setup-testing-db.sh` to rebuild the testing DB. "
            "Only if the user explicitly asked to reset the dev DB, prefix DB_ALLOW_DESTRUCTIVE=true.",
            file=sys.stderr,
        )
        return 2

    if "config:cache" in command and re.search(r"\bssh\b|/var/www/ravenclip|ravenclip-", command):
        print(
            "BLOCKED: `config:cache` on production. app/Ai/KeyPool reads *_API_KEYS via env() at "
            "runtime; a cached config stops .env loading and silently kills enrichment "
            "(docs/deployment.md). Use `php artisan config:clear` instead; route:/view:/event:cache "
            "are fine.",
            file=sys.stderr,
        )
        return 2

    runs_php_tooling = re.search(r"php +artisan\b|vendor/bin/(pint|pest|phpunit)\b", command)
    if runs_php_tooling and "docker compose" not in command and not re.search(r"\bssh\b", command):
        print(
            "BLOCKED: there is no PHP on the host — artisan/pint/pest must run inside the app "
            "container: `docker compose exec -T app php artisan <cmd>` / "
            "`docker compose exec -T app vendor/bin/pint --dirty` (see CLAUDE.md).",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
