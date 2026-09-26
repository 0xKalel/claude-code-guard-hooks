"""The guard is only trustworthy if its blocking behaviour is proven.

Each test feeds the hook the same JSON payload Claude Code sends on
PreToolUse and asserts on the exit code: 0 lets the command run, 2 blocks
it and shows stderr to the agent.
"""

import json
import pathlib
import subprocess

HOOK = pathlib.Path(__file__).resolve().parent.parent / "hooks" / "guard-bash.py"


def run_hook(command=None, raw_stdin=None):
    payload = raw_stdin if raw_stdin is not None else json.dumps(
        {"tool_input": {"command": command}}
    )
    return subprocess.run(
        ["python3", str(HOOK)], input=payload, capture_output=True, text=True
    )


def assert_blocked(result, needle):
    assert result.returncode == 2, result.stderr
    assert "BLOCKED" in result.stderr
    assert needle in result.stderr


# --- Rule 1: destructive migrations -------------------------------------

def test_migrate_fresh_is_blocked():
    assert_blocked(run_hook("php artisan migrate:fresh --seed"), "destructive migration")


def test_db_wipe_is_blocked_even_inside_docker():
    assert_blocked(
        run_hook("docker compose exec -T app php artisan db:wipe"),
        "destructive migration",
    )


def test_explicit_override_is_allowed():
    r = run_hook(
        "DB_ALLOW_DESTRUCTIVE=true docker compose exec -T app php artisan migrate:fresh"
    )
    assert r.returncode == 0


def test_plain_migrate_is_allowed():
    assert run_hook("docker compose exec -T app php artisan migrate").returncode == 0


# --- Rule 2: config:cache against production -----------------------------

def test_config_cache_over_ssh_is_blocked():
    assert_blocked(
        run_hook("ssh deploy@prod 'php artisan config:cache'"), "config:cache"
    )


def test_config_cache_on_prod_path_is_blocked():
    assert_blocked(
        run_hook("cd /var/www/ravenclip && php artisan config:cache"), "config:cache"
    )


def test_other_caches_over_ssh_are_allowed():
    assert run_hook("ssh deploy@prod 'php artisan route:cache'").returncode == 0


# --- Rule 3: PHP tooling must run in the container ------------------------

def test_bare_artisan_is_blocked():
    assert_blocked(run_hook("php artisan tinker"), "no PHP on the host")


def test_bare_pest_is_blocked():
    assert_blocked(run_hook("vendor/bin/pest --dirty"), "no PHP on the host")


def test_artisan_inside_container_is_allowed():
    assert run_hook("docker compose exec -T app vendor/bin/pint --dirty").returncode == 0


def test_artisan_over_ssh_is_allowed():
    # Production runs native PHP; ssh lines are exempt from rule 3 only.
    assert run_hook("ssh deploy@prod 'php artisan queue:restart'").returncode == 0


# --- Fail-open plumbing ---------------------------------------------------

def test_unrelated_commands_pass_through():
    assert run_hook("git status && ls -la").returncode == 0


def test_empty_command_passes_through():
    assert run_hook("").returncode == 0


def test_malformed_stdin_fails_open():
    # A broken payload must never block the agent's real work.
    assert run_hook(raw_stdin="not json{").returncode == 0
