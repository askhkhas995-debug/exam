from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

from .ui import RenderContext, format_kv, render_separator, status_marker
from .vogsphere import paths as vog_paths, sanitize_repo_name


@dataclass(frozen=True)
class SourceResolution:
    source: str
    path: Path
    label: str
    repository: str | None = None
    commit: str | None = None

    @property
    def is_vogsphere(self) -> bool:
        return self.source == "vog"


@dataclass(frozen=True)
class SourceError:
    source: str
    reason: str


class SourceSession:
    def __init__(self, base, source_dir: Path):
        self._base = base
        self.rendu_dir = source_dir

    def __getattr__(self, name: str):
        return getattr(self._base, name)


def resolve_source(root: Path, source: str, *, preferred_name: str | None = None) -> SourceResolution | SourceError:
    if source == "rendu":
        return SourceResolution(
            source="rendu",
            path=root / "workspace" / "rendu",
            label="workspace/rendu",
        )
    if source != "vog":
        return SourceError(source=source, reason=f"unsupported source `{source}`")

    state = _load_vog_state(root)
    submitted = _submitted_snapshots(root, state)
    if not submitted:
        return SourceError(source=source, reason="no submitted snapshot")

    chosen = None
    preferred = sanitize_repo_name(preferred_name) if preferred_name else None
    if preferred:
        chosen = next((item for item in submitted if item["repository"] == preferred), None)
    if chosen is None:
        chosen = max(submitted, key=lambda item: item["submitted_at"])

    snapshot = chosen["path"]
    if not snapshot.exists() or not snapshot.is_dir():
        return SourceError(source=source, reason="submitted snapshot missing")

    return SourceResolution(
        source="vog",
        path=snapshot,
        label="Vogsphere submitted snapshot",
        repository=chosen["repository"],
        commit=chosen["commit"],
    )


@contextmanager
def materialized_source(resolution: SourceResolution) -> Iterator[Path]:
    if not resolution.is_vogsphere:
        yield resolution.path
        return

    with tempfile.TemporaryDirectory(prefix="pforge-vog-source-") as tmp:
        target = Path(tmp) / "rendu"
        _copy_tree_safely(resolution.path, target)
        yield target


def source_session(session, source_dir: Path) -> SourceSession:
    return SourceSession(session, source_dir)


def render_source_error(error: SourceError, *, ctx: RenderContext | None = None) -> str:
    title = "Vogsphere Source" if error.source == "vog" else "Correction Source"
    lines = [
        render_separator(title, ctx=ctx),
        "",
        format_kv("Status", status_marker("KO", ctx), ctx=ctx),
        format_kv("Reason", error.reason, ctx=ctx),
    ]
    if error.source == "vog" and error.reason == "no submitted snapshot":
        lines.extend(
            [
                "",
                render_separator("Hint", ctx=ctx),
                "Run:",
                '  pforge vog commit -m "message" <name>',
                "  pforge vog push <name>",
                "  pforge vog submit <name>",
            ]
        )
    return "\n".join(lines)


def render_source_lines(resolution: SourceResolution, *, ctx: RenderContext | None = None) -> list[str]:
    if resolution.is_vogsphere:
        return [
            format_kv("Source", resolution.label, ctx=ctx),
            format_kv("Repository", resolution.repository or "unknown", ctx=ctx),
            format_kv("Commit", resolution.commit or "unknown", ctx=ctx),
        ]
    return [format_kv("Source", "workspace/rendu", ctx=ctx, role="path")]


def trace_source(resolution: SourceResolution) -> dict[str, str | None]:
    return {
        "source": resolution.source,
        "label": resolution.label,
        "repository": resolution.repository,
        "commit": resolution.commit,
    }


def _load_vog_state(root: Path) -> dict:
    state_file = vog_paths(root).state_file
    if not state_file.exists():
        return {"repos": {}}
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"repos": {}}
    data.setdefault("repos", {})
    return data


def _submitted_snapshots(root: Path, state: dict) -> list[dict]:
    p = vog_paths(root)
    out: list[dict] = []
    for raw_name, repo in (state.get("repos") or {}).items():
        repository = sanitize_repo_name(str(repo.get("name") or raw_name))
        commit_id = repo.get("submitted")
        if not commit_id:
            continue
        commit = _commit_by_id(repo, str(commit_id))
        submitted_at = _submitted_at(repo, str(commit_id)) or str(commit.get("timestamp", ""))
        out.append(
            {
                "repository": repository,
                "commit": str(commit_id),
                "submitted_at": submitted_at,
                "path": p.repos / repository / "commits" / str(commit_id),
            }
        )
    return out


def _commit_by_id(repo: dict, commit_id: str) -> dict:
    for commit in repo.get("commits", []) or []:
        if str(commit.get("id")) == commit_id:
            return commit
    return {}


def _submitted_at(repo: dict, commit_id: str) -> str | None:
    for event in reversed(repo.get("events", []) or []):
        if event.get("type") == "submit" and str(event.get("commit")) == commit_id:
            return str(event.get("timestamp", ""))
    return None


def _copy_tree_safely(source: Path, target: Path) -> None:
    source_root = source.resolve()
    target.mkdir(parents=True, exist_ok=True)
    target_root = target.resolve()
    for item in sorted(source.rglob("*")):
        rel = item.relative_to(source)
        if item.is_symlink():
            raise ValueError(f"unsafe symlink rejected: {rel.as_posix()}")
        if not item.resolve().is_relative_to(source_root):
            raise ValueError(f"unsafe path rejected: {rel.as_posix()}")
        dst = target / rel
        if not dst.resolve().parent.is_relative_to(target_root):
            raise ValueError(f"unsafe path rejected: {rel.as_posix()}")
        if item.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if item.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)
