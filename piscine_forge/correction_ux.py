from __future__ import annotations

from pathlib import Path

from .curriculum import exam_context
from .failure_labels import human_reason_for
from .ui import RenderContext, format_kv, render_separator, status_marker


def mode_key(state: dict | None) -> str:
    state = state or {}
    if state.get("mode"):
        return str(state["mode"])
    if state.get("kind") == "exam":
        return "exam"
    if state.get("pool_id"):
        return "curriculum"
    return "none"


def is_exam(state: dict | None) -> bool:
    return mode_key(state) == "exam"


def is_curriculum(state: dict | None) -> bool:
    return mode_key(state) == "curriculum"


def is_project(state: dict | None) -> bool:
    return mode_key(state) == "project"


def display_mode(state: dict | None) -> str:
    mode = mode_key(state)
    if mode == "exam":
        return "Exam"
    if mode == "curriculum":
        return "Piscine"
    if mode == "project":
        return "Project"
    if mode == "exercise":
        return "Exercise"
    return "None" if mode == "none" else mode.title()


def correction_label(state: dict | None) -> str:
    if is_exam(state):
        return "Grademe"
    if is_curriculum(state):
        return "Moulinette"
    if is_project(state):
        return "Project Moulinette"
    return "Correction"


def correction_menu_label(state: dict | None) -> str:
    return correction_label(state) if state else "Correct / Submit"


def last_correction_label(state: dict | None) -> str:
    return f"Last {correction_label(state)}"


def current_item_label(state: dict | None) -> str:
    if is_project(state):
        return "Project"
    return "Exercise" if is_exam(state) else "Subject"


def human_reason(trace_or_result: dict | None) -> str:
    return human_reason_for(trace_or_result)


def display_reason(state: dict | None, trace_or_result: dict | None) -> str:
    trace_or_result = trace_or_result or {}
    raw = trace_or_result.get("failure_reason") or trace_or_result.get("reason") or ""
    if is_curriculum(state):
        return human_reason(trace_or_result)
    return raw or human_reason(trace_or_result)


def correction_hint(trace_or_result: dict | None) -> str:
    trace_or_result = trace_or_result or {}
    category = trace_or_result.get("failure_category") or trace_or_result.get("reason") or trace_or_result.get("failure_reason")
    hints = {
        "missing_file": "Put the required file in workspace/rendu/",
        "nothing_turned_in": "Add files to workspace/rendu/",
        "wrong_stdout": "Run pforge trace for details",
        "wrong_stderr": "Run pforge trace for details",
    }
    return hints.get(str(category), "")


def _rel(root: Path, path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _friendly_check_name(name: str, state: dict | None) -> str | None:
    if is_curriculum(state) and name in {"hidden_main"}:
        return "tests"
    if is_curriculum(state) and name.startswith("test_"):
        return "tests"
    if name == "expected_files":
        return "expected files"
    if name == "extra_files":
        return "extra files"
    if name == "forbidden_functions":
        return "forbidden functions"
    if name == "main_rejected":
        return None
    return name.replace("_", " ")


def _checks_for_display(trace: dict, state: dict | None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    tests_status = "OK"
    saw_tests = False
    for check in trace.get("checks", []) or []:
        name = str(check.get("name", "check"))
        status = str(check.get("status", "?"))
        label = _friendly_check_name(name, state)
        if label is None and status == "OK":
            continue
        if label is None:
            label = name.replace("_", " ")
        if label == "tests":
            saw_tests = True
            if status != "OK":
                tests_status = status
            continue
        rows.append((label, status))
    if saw_tests:
        rows.append(("tests", tests_status))
    return rows


def render_correction_result(
    *,
    root: Path,
    state: dict | None,
    trace: dict,
    trace_file: Path | None,
    attempts: int | None = None,
    outcome: str | None = None,
    repo=None,
    ctx: RenderContext | None = None,
) -> str:
    label = correction_label(state)
    subject_label = current_item_label(state)
    reason = display_reason(state, trace)
    hint = correction_hint(trace)
    lines = [
        render_separator(label, ctx=ctx),
        "",
    ]
    if is_exam(state) and repo is not None:
        info = exam_context(repo, state or {})
        lines.extend(
            [
                format_kv("Exam", info["exam"], ctx=ctx),
                format_kv("Level", f"{info['level']} / {info['level_count']}", ctx=ctx),
                format_kv("Exercise", trace.get("subject_id", "unknown"), ctx=ctx),
            ]
        )
    else:
        lines.append(format_kv(subject_label, trace.get("subject_id", "unknown"), ctx=ctx))
    lines.append(format_kv("Status", status_marker(trace.get("status"), ctx), ctx=ctx))
    if reason:
        lines.append(format_kv("Reason", reason, ctx=ctx))
    if hint and trace.get("status") != "OK":
        lines.append(format_kv("Hint", hint, ctx=ctx))
    if attempts is not None:
        lines.append(format_kv("Attempts", attempts, ctx=ctx))
    lines.append(format_kv("Trace", _rel(root, trace_file), ctx=ctx, role="path"))

    checks = _checks_for_display(trace, state)
    if checks:
        lines.extend(["", render_separator("Checks", ctx=ctx), ""])
        for name, status in checks:
            lines.append(format_kv(name, status_marker(status, ctx), ctx=ctx))

    if outcome and is_exam(state):
        lines.extend(["", render_separator("Next", ctx=ctx), "", outcome])
    elif outcome:
        lines.extend(["", outcome])
    return "\n".join(lines)
