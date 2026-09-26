import json
import pathlib
import subprocess

HOOK = (
    pathlib.Path(__file__).resolve().parent.parent / "hooks" / "config-edit-reminder.py"
)


def run_hook(file_path=None, raw_stdin=None):
    payload = raw_stdin if raw_stdin is not None else json.dumps(
        {"tool_input": {"file_path": file_path}}
    )
    return subprocess.run(
        ["python3", str(HOOK)], input=payload, capture_output=True, text=True
    )


def test_config_edit_emits_reminder():
    r = run_hook("/app/config/services.php")
    assert r.returncode == 0
    out = json.loads(r.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "restart horizon" in ctx
    assert "/app/config/services.php" in ctx


def test_non_config_edit_stays_silent():
    r = run_hook("/app/app/Models/User.php")
    assert r.returncode == 0
    assert r.stdout == ""


def test_config_lookalike_path_stays_silent():
    assert run_hook("/app/config/nested/deep.php").stdout == ""


def test_malformed_stdin_fails_open():
    assert run_hook(raw_stdin="{{").returncode == 0
