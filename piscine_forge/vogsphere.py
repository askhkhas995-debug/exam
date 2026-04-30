from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import fnmatch
import hashlib
import json
import shutil

from .trace import utc_timestamp
from .ui import RenderContext, format_kv, render_separator, status_marker


STATE_VERSION = 1
IGNORE_NAMES = {"a.out", "__pycache__", ".DS_Store", ".git"}
IGNORE_PATTERNS = ["*.o", "*.out"]


@dataclass(frozen=True)
class VogPaths:
    root: Path
    workspace: Path
    rendu: Path
    store: Path
    repos: Path
    state_file: Path


def paths(root: Path) -> VogPaths:
    root = root.resolve()
    store = root / "workspace" / "vogsphere"
    return VogPaths(
        root=root,
        workspace=root / "workspace",
        rendu=root / "workspace" / "rendu",
        store=store,
        repos=store / "repos",
        state_file=store / "state.json",
    )


def default_repo_name(state: dict | None = None) -> str:
    state = state or {}
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0) or 0)
    if selected and 0 <= index < len(selected):
        subject_id = selected[index].get("subject_id")
        if subject_id:
            return sanitize_repo_name(str(subject_id))
    return "rendu"


def sanitize_repo_name(name: str | None) -> str:
    text = (name or "rendu").strip()
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in text)
    safe = safe.strip("._-/")
    if not safe:
        return "rendu"
    return safe[:80]


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_state(root: Path) -> dict[str, Any]:
    p = paths(root)
    if not p.state_file.exists():
        return {"version": STATE_VERSION, "repos": {}}
    try:
        data = json.loads(p.state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    data.setdefault("version", STATE_VERSION)
    data.setdefault("repos", {})
    return data


def _save_state(root: Path, state: dict[str, Any]) -> None:
    p = paths(root)
    p.store.mkdir(parents=True, exist_ok=True)
    p.repos.mkdir(parents=True, exist_ok=True)
    p.state_file.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _repo_state(root: Path, name: str) -> dict[str, Any] | None:
    return _load_state(root).get("repos", {}).get(sanitize_repo_name(name))


def _ensure_repo(state: dict[str, Any], name: str) -> dict[str, Any]:
    repos = state.setdefault("repos", {})
    safe = sanitize_repo_name(name)
    now = utc_timestamp()
    if safe not in repos:
        repos[safe] = {
            "name": safe,
            "created_at": now,
            "last_commit": None,
            "last_push": None,
            "submitted": None,
            "commits": [],
            "events": [{"type": "init", "timestamp": now}],
        }
    return repos[safe]


def _ignored(rel: Path) -> bool:
    for part in rel.parts:
        if part in IGNORE_NAMES:
            return True
    name = rel.name
    return any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE_PATTERNS)


def _visible_files(rendu: Path) -> tuple[list[Path], str | None]:
    if not rendu.exists():
        return [], None
    files: list[Path] = []
    for item in sorted(rendu.rglob("*")):
        rel = item.relative_to(rendu)
        if _ignored(rel):
            continue
        if item.is_symlink():
            return [], f"unsafe symlink rejected: {rel.as_posix()}"
        if item.is_dir():
            continue
        if item.is_file():
            files.append(rel)
    return files, None


def _tree_hash(rendu: Path, files: list[Path]) -> str:
    digest = hashlib.sha1()
    for rel in files:
        path = rendu / rel
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _short_commit_id(name: str, message: str, tree_hash: str, timestamp: str) -> str:
    digest = hashlib.sha1()
    digest.update(name.encode("utf-8"))
    digest.update(message.encode("utf-8"))
    digest.update(tree_hash.encode("ascii"))
    digest.update(timestamp.encode("ascii"))
    return digest.hexdigest()[:7]


def _copy_snapshot(rendu: Path, files: list[Path], target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    for rel in files:
        src = rendu / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.resolve().is_relative_to(root):
            raise ValueError(f"unsafe path rejected: {rel.as_posix()}")
        shutil.copy2(src, dst)


def _last_commit(repo: dict[str, Any]) -> dict[str, Any] | None:
    last_id = repo.get("last_commit")
    for commit in reversed(repo.get("commits", []) or []):
        if commit.get("id") == last_id:
            return commit
    commits = repo.get("commits", []) or []
    return commits[-1] if commits else None


def _working_tree_state(root: Path, repo: dict[str, Any] | None) -> tuple[str, list[Path], str | None, str | None]:
    p = paths(root)
    p.rendu.mkdir(parents=True, exist_ok=True)
    files, error = _visible_files(p.rendu)
    if error:
        return "unsafe", files, None, error
    if not files:
        return "empty", files, None, None
    tree_hash = _tree_hash(p.rendu, files)
    commit = _last_commit(repo or {})
    if commit and commit.get("tree_hash") == tree_hash:
        return "clean", files, tree_hash, None
    return "modified", files, tree_hash, None


def init_repo(root: Path, name: str | None = None, *, ctx: RenderContext | None = None) -> tuple[int, str]:
    safe = sanitize_repo_name(name)
    state = _load_state(root)
    repo = _ensure_repo(state, safe)
    p = paths(root)
    (p.repos / safe / "commits").mkdir(parents=True, exist_ok=True)
    _save_state(root, state)
    lines = [
        render_separator("Vogsphere Init", ctx=ctx),
        "",
        format_kv("Mode", "local educational simulation", ctx=ctx),
        format_kv("Repository", repo["name"], ctx=ctx),
        format_kv("Remote store", _rel(p.root, p.repos / safe), ctx=ctx, role="path"),
        format_kv("Status", status_marker("OK", ctx), ctx=ctx),
    ]
    return 0, "\n".join(lines)


def render_status(root: Path, name: str | None = None, *, ctx: RenderContext | None = None) -> str:
    safe = sanitize_repo_name(name)
    state = _load_state(root)
    repo = state.get("repos", {}).get(safe)
    p = paths(root)
    working, _files, _tree_hash_value, error = _working_tree_state(root, repo)
    last = _last_commit(repo or {})
    last_text = f'{last["id"]} "{last.get("message", "")}"' if last else "none"
    last_push = "yes" if repo and repo.get("last_push") else "no"
    submitted = "yes" if repo and repo.get("submitted") else "no"
    lines = [
        render_separator("Vogsphere Status", ctx=ctx),
        "",
        format_kv("Mode", "local educational simulation", ctx=ctx),
        format_kv("Repository", safe, ctx=ctx),
        format_kv("Workspace", _rel(p.root, p.rendu), ctx=ctx, role="path"),
        format_kv("Remote store", _rel(p.root, p.repos / safe), ctx=ctx, role="path"),
        "",
        format_kv("State", "initialized" if repo else "not initialized", ctx=ctx),
        format_kv("Working tree", working, ctx=ctx),
        format_kv("Last commit", last_text, ctx=ctx),
        format_kv("Last push", last_push, ctx=ctx),
        format_kv("Submitted", submitted, ctx=ctx),
    ]
    if error:
        lines.append(format_kv("Warning", error, ctx=ctx))
    return "\n".join(lines)


def commit_repo(
    root: Path,
    name: str | None = None,
    *,
    message: str,
    ctx: RenderContext | None = None,
) -> tuple[int, str]:
    safe = sanitize_repo_name(name)
    state = _load_state(root)
    repo = state.get("repos", {}).get(safe)
    p = paths(root)
    if repo is None:
        return _error("Vogsphere Commit", f"Repository `{safe}` is not initialized. Run `pforge vog init {safe}` first.", ctx)
    files, error = _visible_files(p.rendu)
    if error:
        return _error("Vogsphere Commit", error, ctx)
    if not files:
        return _error("Vogsphere Commit", "workspace/rendu is empty; nothing to commit.", ctx)
    timestamp = utc_timestamp()
    tree_hash = _tree_hash(p.rendu, files)
    commit_id = _short_commit_id(safe, message, tree_hash, timestamp)
    commit_dir = p.repos / safe / "commits" / commit_id
    _copy_snapshot(p.rendu, files, commit_dir)
    commit = {
        "id": commit_id,
        "message": message,
        "timestamp": timestamp,
        "tree_hash": tree_hash,
        "files": [rel.as_posix() for rel in files],
    }
    repo.setdefault("commits", []).append(commit)
    repo["last_commit"] = commit_id
    repo.setdefault("events", []).append({"type": "commit", "timestamp": timestamp, "commit": commit_id, "message": message})
    _save_state(root, state)
    lines = [
        render_separator("Vogsphere Commit", ctx=ctx),
        "",
        format_kv("Repository", safe, ctx=ctx),
        format_kv("Snapshot", _rel(p.root, p.rendu), ctx=ctx, role="path"),
        format_kv("Commit", commit_id, ctx=ctx),
        format_kv("Message", message, ctx=ctx),
        format_kv("Status", status_marker("OK", ctx), ctx=ctx),
    ]
    return 0, "\n".join(lines)


def log_lines(root: Path, name: str | None = None, *, ctx: RenderContext | None = None) -> tuple[int, str]:
    safe = sanitize_repo_name(name)
    repo = _repo_state(root, safe)
    if repo is None:
        return _error("Vogsphere Log", f"Repository `{safe}` is not initialized.", ctx)
    lines = [render_separator("Vogsphere Log", ctx=ctx), "", format_kv("Repository", safe, ctx=ctx), ""]
    commits = repo.get("commits", []) or []
    if not commits:
        lines.append("No commits yet.")
    else:
        for commit in reversed(commits):
            lines.append(f"{commit['id']}  {commit.get('timestamp', '')}  {commit.get('message', '')}")
    return 0, "\n".join(lines)


def push_repo(root: Path, name: str | None = None, *, ctx: RenderContext | None = None) -> tuple[int, str]:
    safe = sanitize_repo_name(name)
    state = _load_state(root)
    repo = state.get("repos", {}).get(safe)
    if repo is None:
        return _error("Vogsphere Push", f"Repository `{safe}` is not initialized.", ctx)
    commit = _last_commit(repo)
    if commit is None:
        return _error("Vogsphere Push", "No local commit to push.", ctx)
    timestamp = utc_timestamp()
    repo["last_push"] = commit["id"]
    repo.setdefault("events", []).append({"type": "push", "timestamp": timestamp, "commit": commit["id"]})
    _save_state(root, state)
    p = paths(root)
    lines = [
        render_separator("Vogsphere Push", ctx=ctx),
        "",
        format_kv("Repository", safe, ctx=ctx),
        format_kv("Commit", commit["id"], ctx=ctx),
        format_kv("Remote store", _rel(p.root, p.repos / safe), ctx=ctx, role="path"),
        format_kv("Status", status_marker("OK", ctx), ctx=ctx),
    ]
    return 0, "\n".join(lines)


def submit_repo(root: Path, name: str | None = None, *, ctx: RenderContext | None = None) -> tuple[int, str]:
    safe = sanitize_repo_name(name)
    state = _load_state(root)
    repo = state.get("repos", {}).get(safe)
    if repo is None:
        return _error("Vogsphere Submit", f"Repository `{safe}` is not initialized.", ctx)
    pushed = repo.get("last_push")
    if not pushed:
        return _error("Vogsphere Submit", "No pushed commit to submit. Run `pforge vog push` first.", ctx)
    timestamp = utc_timestamp()
    repo["submitted"] = pushed
    repo.setdefault("events", []).append({"type": "submit", "timestamp": timestamp, "commit": pushed})
    _save_state(root, state)
    lines = [
        render_separator("Vogsphere Submit", ctx=ctx),
        "",
        format_kv("Repository", safe, ctx=ctx),
        format_kv("Submitted", pushed, ctx=ctx),
        format_kv("Status", status_marker("OK", ctx), ctx=ctx),
    ]
    return 0, "\n".join(lines)


def history_lines(root: Path, name: str | None = None, *, ctx: RenderContext | None = None) -> tuple[int, str]:
    safe = sanitize_repo_name(name)
    repo = _repo_state(root, safe)
    if repo is None:
        return _error("Vogsphere History", f"Repository `{safe}` is not initialized.", ctx)
    lines = [render_separator("Vogsphere History", ctx=ctx), "", format_kv("Repository", safe, ctx=ctx), ""]
    events = repo.get("events", []) or []
    if not events:
        lines.append("No history yet.")
    else:
        for event in events:
            parts = [str(event.get("timestamp", "")), str(event.get("type", ""))]
            if event.get("commit"):
                parts.append(str(event["commit"]))
            if event.get("message"):
                parts.append(str(event["message"]))
            lines.append("  ".join(part for part in parts if part))
    return 0, "\n".join(lines)


def _error(title: str, message: str, ctx: RenderContext | None = None) -> tuple[int, str]:
    lines = [
        render_separator(title, ctx=ctx),
        "",
        format_kv("Status", status_marker("KO", ctx), ctx=ctx),
        format_kv("Reason", message, ctx=ctx),
    ]
    return 1, "\n".join(lines)
