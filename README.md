# claude-code-guard-hooks

Two small [Claude Code hooks](https://docs.claude.com/en/docs/claude-code/hooks) from a production SaaS ([RavenClip](https://ravenclip.com)) where agents write most of the code — with the test harness that proves they block what they claim to block.

Rules in a `CLAUDE.md` are advice; an agent under pressure will eventually ignore advice. A hook is enforcement. These are the two smallest pieces of my agent setup that carry the most weight.

## The bash guard (`hooks/guard-bash.py`)

A `PreToolUse` hook that blocks the three command classes agents actually got wrong in this project — each rule exists because something happened:

1. **Destructive migrations** (`migrate:fresh`, `db:wipe`, …). The dev database holds real data; one eager "let me just rebuild the schema" would destroy it. Blocked unless the command carries an explicit `DB_ALLOW_DESTRUCTIVE=true`, which the agent may only add when the user asked for a reset.
2. **`config:cache` aimed at production.** The app reads rotating API key pools via `env()` at runtime; a cached config silently stops `.env` loading and kills the pipeline with no error — the worst kind of outage. Blocked whenever the command also mentions ssh or a production path; `route:`/`view:`/`event:cache` stay allowed.
3. **Bare `php artisan` / `pint` / `pest` on the host.** There is no PHP on the host — everything runs in the `app` container. Blocked with the exact replacement command in the message, so the agent self-corrects on the next attempt. Production commands over ssh legitimately run native artisan, so ssh lines are exempt from this rule only.

The mechanism: **exit 2 + stderr blocks the call, and the stderr text is shown to the agent.** A good block message is not an error — it's a correction that teaches the agent the right command in the same turn.

## The config-edit reminder (`hooks/config-edit-reminder.py`)

A `PostToolUse` hook for the failure mode nobody sees: after editing `config/*.php`, queued workers keep running with the stale config until Horizon restarts. Instead of blocking anything, it injects `additionalContext` so the agent is told, right after the edit, that a restart is needed. Reminders for things an agent can't know from the code are the quiet half of a good hook setup.

## Design rules both hooks follow

- **Fail open.** A malformed payload returns 0. A broken guard must never paralyse real work — the tests pin this behaviour down.
- **Block with the fix, not just the refusal.** Every message contains the command the agent should run instead.
- **Escape hatch, made deliberate.** Overrides exist (`DB_ALLOW_DESTRUCTIVE=true`) but must be typed explicitly, which turns "oops" into a decision.

## Wiring

`settings.example.json` shows the exact wiring; it goes in your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse":  [{ "matcher": "Bash",       "hooks": [{ "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash.py\"" }] }],
    "PostToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/config-edit-reminder.py\"" }] }]
  }
}
```

## Tests

```bash
python3 -m pytest tests/
```

18 cases: every rule's block, every exemption (the docker path, the ssh path, the explicit override), and the fail-open plumbing. If you adapt the regexes to your own project, the harness is the part you should keep.

## Adapting it

The hooks are deliberately not a framework — they're ~100 lines of Python you should read and edit. Swap the regexes for your own forbidden commands, keep the three design rules above, and write the test first.

---

Part of how I ship with agents: specs in, human review before anything lands. More at [0xkalel.github.io/how-i-work](https://0xkalel.github.io/how-i-work/).
