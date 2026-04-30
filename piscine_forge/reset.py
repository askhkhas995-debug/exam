from __future__ import annotations

from pathlib import Path
import shutil

from .progress import progress_path
from .session import Session


class ResetCancelled(Exception):
    pass


def _confirm(message: str, *, yes: bool, input_func=input) -> None:
    if yes:
        return
    try:
        answer = input_func(f"{message} Type 'yes' to continue: ").strip().lower()
    except EOFError as exc:
        raise ResetCancelled("Reset cancelled.") from exc
    if answer != "yes":
        raise ResetCancelled("Reset cancelled.")


def _assert_inside(parent: Path, child: Path) -> None:
    parent = parent.resolve()
    child = child.resolve()
    if child != parent and parent not in child.parents:
        raise RuntimeError(f"Refusing to reset unsafe path: {child}")


def _clear_directory_contents(path: Path) -> list[Path]:
    path.mkdir(parents=True, exist_ok=True)
    deleted: list[Path] = []
    for item in list(path.iterdir()):
        if item.name == ".gitkeep":
            continue
        _assert_inside(path, item)
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
        deleted.append(item)
    return deleted


def reset_session(session: Session, *, yes: bool = False, input_func=input) -> list[Path]:
    del yes, input_func
    session.ensure()
    deleted: list[Path] = []
    if session.state_path.exists():
        _assert_inside(session.workspace, session.state_path)
        session.state_path.unlink()
        deleted.append(session.state_path)
    deleted.extend(_clear_directory_contents(session.subject_dir))
    return deleted


def reset_progress(session: Session, *, yes: bool = False, input_func=input) -> list[Path]:
    _confirm("This deletes workspace/progress.json.", yes=yes, input_func=input_func)
    target = progress_path(session.root)
    deleted: list[Path] = []
    if target.exists():
        _assert_inside(session.workspace, target)
        target.unlink()
        deleted.append(target)
    return deleted


def reset_traces(session: Session, *, yes: bool = False, input_func=input) -> list[Path]:
    _confirm("This deletes generated files under workspace/traces.", yes=yes, input_func=input_func)
    return _clear_directory_contents(session.trace_dir)


def reset_all(session: Session, *, yes: bool = False, input_func=input) -> list[Path]:
    _confirm(
        "This deletes session state, progress, and generated traces. workspace/rendu is kept.",
        yes=yes,
        input_func=input_func,
    )
    deleted: list[Path] = []
    deleted.extend(reset_session(session, yes=True, input_func=input_func))
    deleted.extend(reset_progress(session, yes=True, input_func=input_func))
    deleted.extend(reset_traces(session, yes=True, input_func=input_func))
    return deleted
