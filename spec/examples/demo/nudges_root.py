"""Find the nudges checkout the demo calls.

The demo pins one commit so the audience call stays the same. Set
PLGKIT_NUDGES_ROOT to skip the download. Otherwise this uses a checkout at
that commit under ~/.cache/plgkit-nudges/.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

NUDGES_SHA = "db82c8caba8309266ef0b8cd39d98d9fb4f89e35"
NUDGES_REMOTE = "https://github.com/plgkit/nudges.git"


def nudges_root():
    env = os.environ.get("PLGKIT_NUDGES_ROOT", "").strip()
    if env:
        root = Path(env)
        _require(root)
        return root
    sibling = Path(__file__).resolve().parents[4] / "nudges"
    if _is_sha(sibling):
        return sibling
    cache = Path.home() / ".cache" / "plgkit-nudges" / NUDGES_SHA
    if not _ready(cache):
        _checkout(cache)
    _require(cache)
    return cache


def _ready(root):
    return (root / "packages" / "python" / "plgkit" / "decide.py").is_file() and (
        root / "packages" / "node" / "src" / "decide.ts"
    ).is_file()


def _require(root):
    if not _ready(root):
        raise SystemExit(
            f"{root} is not a nudges checkout at {NUDGES_SHA}. "
            "Set PLGKIT_NUDGES_ROOT or let the demo download it."
        )


def _is_sha(root):
    if not _ready(root):
        return False
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == NUDGES_SHA


def _checkout(cache):
    if cache.exists():
        shutil.rmtree(cache)
    cache.parent.mkdir(parents=True, exist_ok=True)
    steps = [
        ["git", "init", str(cache)],
        ["git", "-C", str(cache), "remote", "add", "origin", NUDGES_REMOTE],
        ["git", "-C", str(cache), "fetch", "--depth", "1", "origin", NUDGES_SHA],
        ["git", "-C", str(cache), "checkout", "--detach", "FETCH_HEAD"],
    ]
    env, cleanup = _git_env()
    try:
        for command in steps:
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False, env=env
            )
            if completed.returncode != 0:
                detail = _redact((completed.stderr or completed.stdout).strip())
                raise SystemExit(f"Could not download nudges {NUDGES_SHA}. {detail}")
    finally:
        cleanup()


def _git_env():
    """Use gh's token when the nudges repo is private. The token stays out of the repo."""
    env = os.environ.copy()
    token = _gh_token()
    if token == "":
        return env, lambda: None
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
    handle.write(f'[url "https://x-access-token:{token}@github.com/"]\n')
    handle.write("\tinsteadOf = https://github.com/\n")
    handle.close()
    os.chmod(handle.name, 0o600)
    env["GIT_CONFIG_GLOBAL"] = handle.name
    env["GIT_CONFIG_SYSTEM"] = os.devnull

    def cleanup():
        try:
            os.remove(handle.name)
        except OSError:
            pass

    return env, cleanup


def _gh_token():
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if shutil.which("gh") is None:
        return ""
    completed = subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _redact(text):
    return re.sub(r"x-access-token:[^@\s]+", "x-access-token:REDACTED", text)
