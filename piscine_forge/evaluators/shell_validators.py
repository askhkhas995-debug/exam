"""Shell-exercise validators for Shell00 and Shell01 Piscine subjects.

Each validator returns (ok: bool, detail: str).  The shell evaluator
dispatches to these based on the ``validator`` field in meta.yml.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import tarfile
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Tar archive inspection
# ---------------------------------------------------------------------------

def validate_tar_archive(
    archive_path: Path,
    expected_contents: list[str] | None = None,
    *,
    forbidden_contents: list[str] | None = None,
) -> tuple[bool, str]:
    """Validate a tar archive exists, is readable, and optionally check contents."""
    if not archive_path.exists():
        return False, f"archive not found: {archive_path.name}"
    try:
        with tarfile.open(archive_path) as tf:
            members = [m.name for m in tf.getmembers()]
    except tarfile.TarError as exc:
        return False, f"invalid tar archive: {exc}"

    if expected_contents is not None:
        missing = [name for name in expected_contents if name not in members]
        if missing:
            return False, f"tar missing entries: {missing}"

    if forbidden_contents:
        found = [name for name in forbidden_contents if name in members]
        if found:
            return False, f"tar contains forbidden entries: {found}"

    return True, f"tar OK ({len(members)} entries)"


def validate_tar_member_properties(
    archive_path: Path,
    member_name: str,
    *,
    expected_mode: int | None = None,
    expected_uid: int | None = None,
    expected_linkname: str | None = None,
    is_symlink: bool | None = None,
) -> tuple[bool, str]:
    """Validate properties of a specific member inside a tar archive."""
    try:
        with tarfile.open(archive_path) as tf:
            try:
                info = tf.getmember(member_name)
            except KeyError:
                return False, f"member {member_name!r} not found in archive"
    except tarfile.TarError as exc:
        return False, f"invalid tar archive: {exc}"

    if is_symlink is not None:
        if is_symlink and not info.issym():
            return False, f"{member_name} should be a symlink"
        if not is_symlink and info.issym():
            return False, f"{member_name} should not be a symlink"

    if expected_mode is not None:
        actual = stat.S_IMODE(info.mode)
        if actual != expected_mode:
            return False, f"{member_name} mode {oct(actual)} != expected {oct(expected_mode)}"

    if expected_uid is not None and info.uid != expected_uid:
        return False, f"{member_name} uid {info.uid} != expected {expected_uid}"

    if expected_linkname is not None:
        if info.linkname != expected_linkname:
            return False, f"{member_name} linkname {info.linkname!r} != expected {expected_linkname!r}"

    return True, f"{member_name} properties OK"


# ---------------------------------------------------------------------------
# Symlink checks
# ---------------------------------------------------------------------------

def validate_symlink(path: Path, expected_target: str | None = None) -> tuple[bool, str]:
    """Validate that *path* is a symlink and optionally points to *expected_target*."""
    if not path.exists(follow_symlinks=False):
        return False, f"file not found: {path.name}"
    if not path.is_symlink():
        return False, f"{path.name} is not a symbolic link"
    actual = os.readlink(path)
    if expected_target is not None and actual != expected_target:
        return False, f"symlink target {actual!r} != expected {expected_target!r}"
    return True, f"symlink OK -> {actual}"


# ---------------------------------------------------------------------------
# Hardlink checks
# ---------------------------------------------------------------------------

def validate_hardlink(path1: Path, path2: Path) -> tuple[bool, str]:
    """Validate that two paths are hard links to the same inode."""
    if not path1.exists():
        return False, f"file not found: {path1.name}"
    if not path2.exists():
        return False, f"file not found: {path2.name}"
    stat1 = os.stat(path1)
    stat2 = os.stat(path2)
    if stat1.st_ino != stat2.st_ino:
        return False, f"not hardlinked: inode {stat1.st_ino} != {stat2.st_ino}"
    if stat1.st_dev != stat2.st_dev:
        return False, f"not hardlinked: different devices"
    return True, f"hardlink OK (inode {stat1.st_ino})"


# ---------------------------------------------------------------------------
# Permission / chmod checks
# ---------------------------------------------------------------------------

def validate_permissions(path: Path, expected_mode: int) -> tuple[bool, str]:
    """Validate file permission bits (e.g. 0o755, 0o644)."""
    if not path.exists(follow_symlinks=False):
        return False, f"file not found: {path.name}"
    actual = stat.S_IMODE(os.stat(path).st_mode)
    if actual != expected_mode:
        return False, f"permissions {oct(actual)} != expected {oct(expected_mode)}"
    return True, f"permissions OK ({oct(actual)})"


# ---------------------------------------------------------------------------
# Timestamp checks
# ---------------------------------------------------------------------------

def validate_timestamp(
    path: Path,
    expected_timestamp: float | None = None,
    *,
    tolerance_seconds: float = 60.0,
    expected_date_str: str | None = None,
) -> tuple[bool, str]:
    """Validate file modification time.

    *expected_date_str* is an ISO-like ``YYYY-MM-DD HH:MM`` string (compared
    against ``ls -l`` style formatting of the mtime).  *expected_timestamp*
    is compared with a *tolerance_seconds* window.
    """
    if not path.exists(follow_symlinks=False):
        return False, f"file not found: {path.name}"

    mtime = os.stat(path).st_mtime

    if expected_timestamp is not None:
        diff = abs(mtime - expected_timestamp)
        if diff > tolerance_seconds:
            return False, f"mtime diff {diff:.0f}s exceeds tolerance {tolerance_seconds:.0f}s"

    if expected_date_str is not None:
        import time
        formatted = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
        if formatted != expected_date_str:
            return False, f"mtime date {formatted!r} != expected {expected_date_str!r}"

    return True, f"timestamp OK"


# ---------------------------------------------------------------------------
# Weird filenames (quotes, backslashes, dollar, asterisks, question marks)
# ---------------------------------------------------------------------------

def validate_weird_filename(directory: Path, expected_name: str) -> tuple[bool, str]:
    """Validate that a file with the exact *expected_name* exists in *directory*.

    The name may contain quotes, backslashes, ``$``, ``*``, ``?``, etc.
    """
    if not directory.is_dir():
        return False, f"directory not found: {directory}"

    target = directory / expected_name
    if target.exists(follow_symlinks=False):
        return True, f"file {expected_name!r} found"

    # List actual files for diagnostics
    actual = [f.name for f in directory.iterdir()]
    return False, f"file {expected_name!r} not found; directory contains: {actual}"


# ---------------------------------------------------------------------------
# Git-specific validators
# ---------------------------------------------------------------------------

def validate_git_commit(
    repo_dir: Path,
    expected_message_contains: str | list[str] | None = None,
    *,
    expected_num_commits: int | None = None,
) -> tuple[bool, str]:
    """Validate git commit history."""
    if not (repo_dir / ".git").exists():
        return False, "not a git repository (no .git directory)"

    try:
        proc = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        return False, "git command not found"
    except subprocess.TimeoutExpired:
        return False, "git log timed out"

    if proc.returncode != 0:
        return False, f"git log failed: {proc.stderr.strip()}"

    lines = [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]

    if expected_num_commits is not None and len(lines) != expected_num_commits:
        return False, f"expected {expected_num_commits} commits, found {len(lines)}"

    if expected_message_contains is not None:
        needles = [expected_message_contains] if isinstance(expected_message_contains, str) else expected_message_contains
        full_log = proc.stdout
        missing = [n for n in needles if n not in full_log]
        if missing:
            return False, f"commit log missing: {missing}"

    return True, f"git commits OK ({len(lines)} commits)"


def validate_git_ignore(
    repo_dir: Path,
    expected_patterns: list[str] | None = None,
) -> tuple[bool, str]:
    """Validate .gitignore contents."""
    gitignore = repo_dir / ".gitignore"
    if not gitignore.exists():
        return False, ".gitignore not found"

    content = gitignore.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    if expected_patterns:
        missing = [p for p in expected_patterns if p not in lines]
        if missing:
            return False, f".gitignore missing patterns: {missing}"

    return True, f".gitignore OK ({len(lines)} patterns)"


# ---------------------------------------------------------------------------
# Find-based exercises (clean, find_sh, count_files)
# ---------------------------------------------------------------------------

def validate_find_output(
    script_path: Path,
    working_dir: Path,
    expected_stdout: str | None = None,
    *,
    stdout_contains: list[str] | None = None,
    timeout: int = 5,
) -> tuple[bool, str]:
    """Run a shell script and validate output for find-based exercises."""
    if not script_path.exists():
        return False, f"script not found: {script_path.name}"

    try:
        proc = subprocess.run(
            ["/bin/sh", str(script_path)],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"

    if proc.returncode != 0:
        return False, f"script exited {proc.returncode}: {proc.stderr.strip()}"

    if expected_stdout is not None and proc.stdout != expected_stdout:
        return False, f"stdout mismatch"

    if stdout_contains:
        missing = [s for s in stdout_contains if s not in proc.stdout]
        if missing:
            return False, f"stdout missing: {missing}"

    return True, "script output OK"


# ---------------------------------------------------------------------------
# /etc/passwd pipeline exercises (r_dwssap.sh etc.)
# ---------------------------------------------------------------------------

def validate_passwd_pipeline(
    script_path: Path,
    *,
    input_text: str | None = None,
    expected_stdout: str | None = None,
    stdout_contains: list[str] | None = None,
    timeout: int = 5,
) -> tuple[bool, str]:
    """Run a passwd-pipeline style script with optional stdin."""
    if not script_path.exists():
        return False, f"script not found: {script_path.name}"

    try:
        proc = subprocess.run(
            ["/bin/sh", str(script_path)],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"

    if expected_stdout is not None and proc.stdout != expected_stdout:
        return False, f"stdout mismatch"

    if stdout_contains:
        missing = [s for s in stdout_contains if s not in proc.stdout]
        if missing:
            return False, f"stdout missing: {missing}"

    return True, "passwd pipeline output OK"


# ---------------------------------------------------------------------------
# File content validator (simple exact or contains check)
# ---------------------------------------------------------------------------

def validate_file_content(
    path: Path,
    expected_content: str | None = None,
    *,
    contains: list[str] | None = None,
    not_contains: list[str] | None = None,
) -> tuple[bool, str]:
    """Validate file content by exact match or substring presence."""
    if not path.exists():
        return False, f"file not found: {path.name}"

    content = path.read_text(encoding="utf-8", errors="replace")

    if expected_content is not None and content != expected_content:
        return False, "content mismatch"

    if contains:
        missing = [s for s in contains if s not in content]
        if missing:
            return False, f"content missing: {missing}"

    if not_contains:
        found = [s for s in not_contains if s in content]
        if found:
            return False, f"content contains forbidden: {found}"

    return True, "file content OK"


def validate_file_matches_fixture(
    path: Path,
    fixture_path: Path,
    *,
    exact: bool = True,
) -> tuple[bool, str]:
    """Validate submitted file content against a private fixture file."""
    if not path.exists():
        return False, f"file not found: {path.name}"
    if not fixture_path.exists():
        return False, f"fixture not found: {fixture_path}"

    actual = path.read_text(encoding="utf-8", errors="replace")
    expected = fixture_path.read_text(encoding="utf-8", errors="replace")
    if exact and actual != expected:
        return False, "content mismatch"
    if not exact and actual.strip() != expected.strip():
        return False, "content mismatch"
    return True, "file matches fixture"


# ---------------------------------------------------------------------------
# Dispatcher – called by the shell evaluator
# ---------------------------------------------------------------------------

VALIDATORS: dict[str, Any] = {
    "tar_archive": validate_tar_archive,
    "tar_member": validate_tar_member_properties,
    "symlink": validate_symlink,
    "hardlink": validate_hardlink,
    "permissions": validate_permissions,
    "timestamp": validate_timestamp,
    "weird_filename": validate_weird_filename,
    "git_commit": validate_git_commit,
    "git_ignore": validate_git_ignore,
    "find_output": validate_find_output,
    "passwd_pipeline": validate_passwd_pipeline,
    "file_content": validate_file_content,
    "file_matches_fixture": validate_file_matches_fixture,
}


def run_validators(
    trace: dict,
    checks: list[dict],
    submit: Path,
    repo_root: Path | None = None,
) -> tuple[bool, str]:
    """Run a list of validator checks defined in tests.yml.

    Each check dict should have:
      - validator: str (key in VALIDATORS)
      - args: dict (keyword arguments for the validator)
      - name: str (optional, for trace naming)

    Returns (all_passed, first_failure_reason).
    """
    from .common import add_check

    for idx, check in enumerate(checks, start=1):
        validator_name = check.get("validator")
        if validator_name not in VALIDATORS:
            add_check(trace, f"validator_{idx}", "ERROR", f"unknown validator: {validator_name}")
            return False, f"unknown validator: {validator_name}"

        validator_fn = VALIDATORS[validator_name]
        args = dict(check.get("args", {}))

        # Resolve path arguments relative to submit directory
        for key in ("path", "path1", "path2", "archive_path", "script_path",
                     "directory", "repo_dir", "working_dir"):
            if key in args and not Path(args[key]).is_absolute():
                args[key] = submit / args[key]
            elif key in args:
                args[key] = Path(args[key])
        for key in ("fixture_path",):
            if key in args and not Path(args[key]).is_absolute():
                args[key] = (repo_root or Path.cwd()) / args[key]
            elif key in args:
                args[key] = Path(args[key])

        ok, detail = validator_fn(**args)
        check_name = check.get("name", f"validator_{validator_name}_{idx}")
        add_check(trace, check_name, "OK" if ok else "KO", detail)

        if not ok:
            return False, f"shell_validator_failure: {detail}"

    return True, ""
