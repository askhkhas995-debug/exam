from __future__ import annotations

from pathlib import Path
import platform
import shutil
import sys

from . import __version__
from .loader import Repository
from .session import Session
from .ui import format_kv, render_separator, status_marker


def _tool_status(name: str, *, optional: bool = False) -> tuple[str, str]:
    path = shutil.which(name)
    if path:
        return "OK", path
    return ("WARN" if optional else "KO"), "not found"


def _current_subject(state: dict) -> str:
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0))
    if selected and 0 <= index < len(selected):
        return str(selected[index].get("subject_id", "none"))
    return "none"


def render_doctor(repo: Repository, session: Session, *, ctx=None) -> tuple[str, int]:
    errors = repo.validate()
    subjects = repo.subjects()
    pools = repo.pools()
    state = session.load_if_exists()
    python_ok = sys.version_info >= (3, 10)
    console = shutil.which("pforge")
    tools = [
        ("python", "OK" if python_ok else "KO", platform.python_version()),
        ("pforge command", "OK" if console else "WARN", console or "not installed on PATH"),
        ("sh", *_tool_status("sh")),
        ("gcc", *_tool_status("gcc", optional=True)),
        ("make", *_tool_status("make", optional=True)),
        ("norminette", *_tool_status("norminette", optional=True)),
    ]
    required_paths = [
        "subjects",
        "corrections",
        "pools",
        "config",
        "workspace/subject",
        "workspace/rendu",
        "workspace/traces",
    ]
    lines = [
        render_separator("PiscineForge Doctor", ctx=ctx),
        "",
        format_kv("Version", __version__, ctx=ctx),
        format_kv("Project root", repo.root, ctx=ctx, role="path"),
        format_kv("Python", platform.python_version(), ctx=ctx),
        "",
        render_separator("Repository", ctx=ctx),
        "",
        format_kv("Subjects", len(subjects), ctx=ctx),
        format_kv("Pools", len(pools), ctx=ctx),
        format_kv("Validation", status_marker("OK" if not errors else "KO", ctx), ctx=ctx),
    ]
    if errors:
        for error in errors[:10]:
            lines.append(f"  {status_marker('KO', ctx)} {error}")
        if len(errors) > 10:
            lines.append(f"  {status_marker('WARN', ctx)} {len(errors) - 10} more validation errors omitted")

    lines.extend(["", render_separator("Workspace", ctx=ctx), ""])
    for rel in required_paths:
        path = repo.root / rel
        marker = status_marker("OK" if path.exists() else "KO", ctx)
        lines.append(format_kv(rel, marker, width=20, ctx=ctx))

    lines.extend(["", render_separator("Commands", ctx=ctx), ""])
    for name, status, detail in tools:
        lines.append(f"{status_marker(status, ctx)} {name:<15} {detail}")

    lines.extend(["", render_separator("Session", ctx=ctx), ""])
    if state:
        lines.append(format_kv("Mode", state.get("mode", state.get("kind", "unknown")), ctx=ctx))
        lines.append(format_kv("Pool", state.get("pool_id", "none"), ctx=ctx))
        lines.append(format_kv("Subject", _current_subject(state), ctx=ctx))
    else:
        lines.append("No active session.")

    failed = bool(errors) or not python_ok
    return "\n".join(lines), 1 if failed else 0
