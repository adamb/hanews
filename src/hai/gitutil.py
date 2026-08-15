from __future__ import annotations

import subprocess
from pathlib import Path

from hai.config import REPO_ROOT


class GitError(Exception):
    pass


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def push_digest(path: Path, digest_date: str) -> str:
    rel = path if path.is_absolute() else REPO_ROOT / path
    try:
        rel = rel.resolve().relative_to(REPO_ROOT)
    except ValueError as exc:
        raise GitError(f"Digest {path} is outside the repo") from exc

    added = _run(["git", "add", str(rel)])
    if added.returncode != 0:
        raise GitError(added.stderr.strip() or "git add failed")

    status = _run(["git", "status", "--porcelain", "--", str(rel)])
    if not status.stdout.strip():
        return "No digest changes to commit."

    commit = _run(["git", "commit", "-m", f"digest: {digest_date}"])
    if commit.returncode != 0:
        raise GitError(commit.stderr.strip() or "git commit failed")

    push = _run(["git", "push", "origin", "HEAD"])
    if push.returncode != 0:
        raise GitError(push.stderr.strip() or "git push failed")
    return f"Pushed {rel} to origin."
