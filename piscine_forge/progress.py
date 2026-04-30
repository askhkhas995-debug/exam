from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import json

from .curriculum import current_curriculum_context, exam_context, exercise_label, module_label
from .exam_ui import render_exam_status
from .correction_ux import (
    correction_label,
    current_item_label,
    display_mode,
    human_reason,
    last_correction_label,
    mode_key,
)
from .trace import latest_trace, utc_timestamp
from .ui import (
    RenderContext,
    format_duration as ui_format_duration,
    format_kv,
    render_progress_bar,
    render_separator,
    status_marker,
)


def progress_path(root: Path) -> Path:
    return root / "workspace" / "progress.json"


def init_progress() -> dict:
    return {
        "version": 2,
        "curricula": {},
        "exams": {},
        "subjects": {},
        "attempt_log": [],
    }


def load_progress(path: Path) -> dict:
    target = progress_path(path) if path.is_dir() else path
    if not target.exists():
        return init_progress()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return init_progress()
    data.setdefault("version", 2)
    data.setdefault("curricula", {})
    data.setdefault("exams", {})
    data.setdefault("subjects", {})
    data.setdefault("attempt_log", [])
    return data


def save_progress(path: Path, data: dict) -> None:
    target = progress_path(path) if path.is_dir() else path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def elapsed_seconds(value: str | None, *, now: datetime | None = None) -> int | None:
    started = _parse_time(value)
    if started is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, int((now - started).total_seconds()))


def format_duration(seconds: int | None) -> str:
    return ui_format_duration(seconds)


def _format_timestamp(value: str | None) -> str:
    parsed = _parse_time(value)
    if parsed is None:
        return "not available"
    return parsed.strftime("%Y-%m-%d %H:%M")


def _mode(state: dict) -> str:
    return mode_key(state)


def _current_item(state: dict) -> dict:
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0))
    if selected and 0 <= index < len(selected):
        return selected[index]
    if state.get("subject_id"):
        return {"subject_id": state["subject_id"]}
    return {}


def current_subject_id(state: dict) -> str | None:
    return _current_item(state).get("subject_id")


def current_module_id(state: dict) -> str | None:
    return _current_item(state).get("module") or state.get("module_id")


def current_level(state: dict) -> object:
    return _current_item(state).get("level", state.get("level"))


def next_subject_id(state: dict) -> str | None:
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0))
    if selected and index + 1 < len(selected):
        return selected[index + 1].get("subject_id")
    return None


def _rel(root: Path, path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _trace_string(root: Path, trace_file: Path | None) -> str:
    return _rel(root, trace_file)


def _exam_key(pool_id: str, seed: int | None) -> str:
    return f"{pool_id}:{seed if seed is not None else 'none'}"


def _human_reason(trace_or_result: dict) -> str:
    return human_reason(trace_or_result)


def _last_result_line(last: dict | None, ctx: RenderContext | None = None) -> str:
    if not last:
        return "none"
    status = last.get("status", "none")
    reason = _human_reason(last)
    marker = status_marker(status, ctx)
    return f"{marker} {reason}" if reason and status != "OK" else marker


def _pool_duration_seconds(repo, state: dict) -> int | None:
    if state.get("duration_seconds") is not None:
        return int(state["duration_seconds"])
    pool_id = state.get("pool_id")
    if not pool_id:
        return None
    try:
        pool = repo.get_pool(pool_id)
    except SystemExit:
        return None
    minutes = pool.get("duration_minutes")
    return int(minutes) * 60 if minutes is not None else None


def _time_lines(repo, state: dict, ctx: RenderContext | None = None) -> list[str]:
    started_at = state.get("started_at")
    elapsed = elapsed_seconds(started_at)
    duration = _pool_duration_seconds(repo, state)
    lines = [
        format_kv("Started at", _format_timestamp(started_at), ctx=ctx),
        format_kv("Elapsed", format_duration(elapsed), ctx=ctx),
    ]
    if duration is None:
        lines.append(format_kv("Time remaining", "not configured", ctx=ctx))
    else:
        remaining = None if elapsed is None else max(0, duration - elapsed)
        lines.append(format_kv("Duration", format_duration(duration), ctx=ctx))
        lines.append(format_kv("Time remaining", format_duration(remaining), ctx=ctx))
    current_elapsed = elapsed_seconds(state.get("current_exercise_started_at"))
    lines.append(format_kv("Current time", format_duration(current_elapsed), ctx=ctx))
    return lines


def init_curriculum_progress(repo, root: Path, pool_id: str, subject_id: str, state: dict | None = None) -> dict:
    data = load_progress(root)
    entry = data.setdefault("curricula", {}).setdefault(
        pool_id,
        {
            "pool_id": pool_id,
            "started_at": (state or {}).get("started_at"),
            "current_subject_id": subject_id,
            "completed": [],
            "failed": {},
            "last_result": None,
        },
    )
    entry.setdefault("completed", [])
    entry.setdefault("failed", {})
    entry.setdefault("last_result", None)
    entry.setdefault("started_at", (state or {}).get("started_at"))
    entry["current_subject_id"] = subject_id
    if state:
        entry["module_id"] = current_module_id(state)
    save_progress(root, data)
    return data


def init_exam_progress(root: Path, pool_id: str, seed: int | None, picked: list[dict], state: dict | None = None) -> dict:
    data = load_progress(root)
    key = _exam_key(pool_id, seed)
    data.setdefault("exams", {})[key] = {
        "pool_id": pool_id,
        "seed": seed,
        "started_at": (state or {}).get("started_at"),
        "duration_seconds": (state or {}).get("duration_seconds"),
        "current_level": (picked[0].get("level") if picked else None),
        "current_subject_id": (picked[0].get("subject_id") if picked else None),
        "picked": [
            {
                "level": item.get("level"),
                "subject_id": item.get("subject_id"),
                "status": item.get("status", "pending"),
                "attempts": int(item.get("attempts", 0)),
            }
            for item in picked
        ],
        "last_result": None,
    }
    save_progress(root, data)
    return data


def record_attempt(repo, session, trace: dict, trace_file: Path | None) -> bool:
    state = session.load_if_exists()
    subject_id = trace.get("subject_id") or current_subject_id(state)
    if not subject_id:
        return False

    data = load_progress(session.root)
    status = trace.get("status", "ERROR")
    ok = status == "OK"
    now = trace.get("timestamp") or utc_timestamp()
    reason = _human_reason(trace)
    raw_reason = trace.get("failure_reason", "")
    category = trace.get("failure_category", "")
    trace_value = _trace_string(session.root, trace_file)
    spent = elapsed_seconds(state.get("current_exercise_started_at"))
    mode = _mode(state)
    pool_id = state.get("pool_id")
    last_result = {
        "pool_id": pool_id,
        "subject_id": subject_id,
        "status": status,
        "reason": reason,
        "failure_reason": raw_reason,
        "failure_category": category,
        "trace": trace_value,
        "timestamp": now,
    }
    if trace.get("returncode") is not None:
        last_result["returncode"] = trace.get("returncode")
    if trace.get("signal"):
        last_result["signal"] = trace.get("signal")
    if spent is not None:
        last_result["time_spent_seconds"] = spent

    subject_entry = data.setdefault("subjects", {}).setdefault(subject_id, {"attempts": 0})
    subject_entry["attempts"] = int(subject_entry.get("attempts", 0)) + 1
    subject_entry["last_result"] = last_result

    attempt = {
        "timestamp": now,
        "mode": mode,
        "pool_id": pool_id,
        "subject_id": subject_id,
        "status": status,
        "reason": reason,
        "failure_reason": raw_reason,
        "failure_category": category,
        "trace": trace_value,
    }
    if trace.get("returncode") is not None:
        attempt["returncode"] = trace.get("returncode")
    if trace.get("signal"):
        attempt["signal"] = trace.get("signal")
    if spent is not None:
        attempt["time_spent_seconds"] = spent
    data.setdefault("attempt_log", []).append(attempt)

    if mode == "exam" and pool_id:
        _record_exam_attempt(data, state, last_result, ok)
    elif pool_id:
        _record_curriculum_attempt(data, state, last_result, ok)

    save_progress(session.root, data)
    return True


def _record_curriculum_attempt(data: dict, state: dict, last_result: dict, ok: bool) -> None:
    pool_id = state["pool_id"]
    subject_id = last_result["subject_id"]
    entry = data.setdefault("curricula", {}).setdefault(
        pool_id,
        {
            "pool_id": pool_id,
            "started_at": state.get("started_at"),
            "current_subject_id": subject_id,
            "completed": [],
            "failed": {},
            "last_result": None,
        },
    )
    entry.setdefault("completed", [])
    entry.setdefault("failed", {})
    entry["last_result"] = last_result
    entry["module_id"] = current_module_id(state)
    if ok:
        if subject_id not in entry["completed"]:
            entry["completed"].append(subject_id)
        entry["current_subject_id"] = next_subject_id(state) or subject_id
    else:
        failed = entry.setdefault("failed", {})
        failed[subject_id] = int(failed.get(subject_id, 0)) + 1
        entry["current_subject_id"] = subject_id


def _record_exam_attempt(data: dict, state: dict, last_result: dict, ok: bool) -> None:
    pool_id = state["pool_id"]
    seed = state.get("seed")
    subject_id = last_result["subject_id"]
    key = _exam_key(pool_id, seed)
    selected = state.get("selected", [])
    entry = data.setdefault("exams", {}).setdefault(
        key,
        {
            "pool_id": pool_id,
            "seed": seed,
            "started_at": state.get("started_at"),
            "duration_seconds": state.get("duration_seconds"),
            "current_level": current_level(state),
            "current_subject_id": subject_id,
            "picked": selected,
            "last_result": None,
        },
    )
    entry.setdefault("picked", selected)
    entry["last_result"] = last_result
    entry["duration_seconds"] = state.get("duration_seconds", entry.get("duration_seconds"))
    for item in entry.get("picked", []):
        if item.get("subject_id") == subject_id:
            item["attempts"] = int(item.get("attempts", 0)) + 1
            item["status"] = "OK" if ok else "KO"
            break
    if ok:
        next_subject = next_subject_id(state)
        entry["current_subject_id"] = next_subject
        if next_subject is None:
            entry["current_level"] = None
        else:
            for item in entry.get("picked", []):
                if item.get("subject_id") == next_subject:
                    entry["current_level"] = item.get("level")
                    break
    else:
        entry["current_subject_id"] = subject_id
        entry["current_level"] = current_level(state)


def _subject_path(root: Path) -> Path:
    return root / "workspace" / "subject" / "subject.en.txt"


def _rendu_path(root: Path) -> Path:
    return root / "workspace" / "rendu"


def _latest_result_for_state(root: Path, data: dict, state: dict) -> dict | None:
    mode = _mode(state)
    pool_id = state.get("pool_id")
    if mode == "exam" and pool_id:
        entry = data.get("exams", {}).get(_exam_key(pool_id, state.get("seed")), {})
        return entry.get("last_result")
    if pool_id:
        entry = data.get("curricula", {}).get(pool_id, {})
        return entry.get("last_result")
    subject = current_subject_id(state)
    if subject:
        return data.get("subjects", {}).get(subject, {}).get("last_result")
    return None


def format_current(repo, root: Path, session_state: dict | None, ctx: RenderContext | None = None) -> str:
    state = session_state or {}
    if not state:
        return "\n".join(
            [
                "No active session.",
                "Start one with:",
                "  pforge start piscine42",
                "  pforge exam <pool>",
                "  pforge menu",
            ]
        )

    data = load_progress(root)
    subject_id = current_subject_id(state) or "none"
    last = _latest_result_for_state(root, data, state)
    attempts = int(data.get("subjects", {}).get(subject_id, {}).get("attempts", 0))
    trace = latest_trace(root / "workspace" / "traces")
    if _mode(state) == "exam":
        info = exam_context(repo, state)
        title = "Current Exercise"
        context_lines = [
            format_kv("Mode", display_mode(state), ctx=ctx),
            format_kv("Exam", f"{info['exam']} ({info['pool_id']})", ctx=ctx),
            format_kv("Level", f"{info['level']} / {info['level_count']}", ctx=ctx),
            format_kv("Exercise", subject_id, ctx=ctx),
            format_kv("Correction", correction_label(state), ctx=ctx),
            format_kv("Next", info["next_subject_id"], ctx=ctx),
        ]
    elif _mode(state) == "curriculum":
        info = current_curriculum_context(repo, state, data)
        title = "Current Subject"
        context_lines = [
            format_kv("Mode", display_mode(state), ctx=ctx),
            format_kv("Correction", correction_label(state), ctx=ctx),
            format_kv("Pool", info["pool_id"], ctx=ctx),
            format_kv("Module", f"{info['module']} ({info['module_id']})", ctx=ctx),
            format_kv("Exercise", info["exercise_id"], ctx=ctx),
            format_kv("Subject", subject_id, ctx=ctx),
            format_kv("Reason", info["reason"], ctx=ctx),
            format_kv("Next", info["next_subject_id"], ctx=ctx),
        ]
    else:
        title = "Current Subject"
        context_lines = [
            format_kv("Mode", display_mode(state), ctx=ctx),
            format_kv("Correction", correction_label(state), ctx=ctx),
            format_kv(current_item_label(state), subject_id, ctx=ctx),
            format_kv("Next", next_subject_id(state) or "none", ctx=ctx),
        ]
    lines = [
        render_separator(title, ctx=ctx),
        "",
        *context_lines,
        format_kv(last_correction_label(state), _last_result_line(last, ctx), ctx=ctx),
        format_kv("Attempts", attempts, ctx=ctx),
        "",
        format_kv("Subject file", _rel(root, _subject_path(root)), ctx=ctx, role="path"),
        format_kv("Rendu", _rel(root, _rendu_path(root)) + "/", ctx=ctx, role="path"),
        format_kv("Trace", _trace_string(root, trace), ctx=ctx, role="path"),
    ]
    return "\n".join(lines)


def summarize_module_progress(repo, root: Path, session_state: dict | None, ctx: RenderContext | None = None) -> str:
    state = session_state or {}
    if not state or _mode(state) != "curriculum":
        return "No active Piscine session."
    data = load_progress(root)
    info = current_curriculum_context(repo, state, data)
    pool_id = state.get("pool_id")
    pool = repo.get_pool(pool_id)
    module_subjects = []
    for module in pool.get("modules", []) or []:
        if str(module.get("id")) == info["module_id"]:
            module_subjects = [str(sid) for sid in module.get("subjects", []) or []]
            break
    entry = data.get("curricula", {}).get(pool_id, {})
    completed = set(entry.get("completed", []) or [])
    failed = entry.get("failed", {}) or {}
    current = current_subject_id(state)
    lines = [
        render_separator(f"{info['module']} Progress", ctx=ctx),
        "",
    ]
    for index, subject_id in enumerate(module_subjects):
        if subject_id in completed:
            marker = status_marker("OK", ctx)
        elif subject_id == current:
            marker = "current"
        elif subject_id in failed:
            marker = status_marker("KO", ctx)
        else:
            marker = "pending"
        lines.append(f"{exercise_label(index):<5} {subject_id:<28} {marker}")
    lines.extend(
        [
            "",
            "Current:",
            f"{info['exercise_id']} {info['subject_id']}",
            "",
            "Next:",
            info["next_subject_id"],
        ]
    )
    return "\n".join(lines)


def summarize_curriculum(repo, root: Path, progress: dict, state: dict, ctx: RenderContext | None = None) -> str:
    pool_id = state.get("pool_id")
    if not pool_id:
        return "No active curriculum session."
    try:
        pool = repo.get_pool(pool_id)
    except SystemExit:
        pool = {"modules": []}
    entry = progress.get("curricula", {}).get(pool_id, {})
    info = current_curriculum_context(repo, state, progress)
    current = current_subject_id(state) or entry.get("current_subject_id") or "none"
    completed = set(entry.get("completed", []))
    failed = entry.get("failed", {})
    selected = state.get("selected", [])
    module_id = current_module_id(state) or entry.get("module_id") or "none"
    module_subjects = [item.get("subject_id") for item in selected if item.get("module") == module_id]
    if not module_subjects:
        for module in pool.get("modules", []):
            if module.get("id") == module_id:
                module_subjects = list(module.get("subjects", []))
                break
    current_index = module_subjects.index(current) + 1 if current in module_subjects else 0
    last = entry.get("last_result")
    failed_attempts = sum(int(value) for value in failed.values())
    started_elapsed = elapsed_seconds(state.get("started_at"))
    day_number = (started_elapsed // 86400) + 1 if started_elapsed is not None else "not available"
    module_done = len([sid for sid in module_subjects if sid in completed])
    last_status = "none"
    last_reason = "none"
    if last:
        last_status = status_marker(last.get("status"), ctx)
        last_reason = _human_reason(last) or "none"
    trace_path = last.get("trace") if last else _trace_string(root, latest_trace(root / "workspace" / "traces"))
    last_subject = last.get("subject_id") if last else current
    attempts = int(progress.get("subjects", {}).get(last_subject, {}).get("attempts", 0)) if last_subject else 0
    lines = [
        render_separator("Piscine Progress", ctx=ctx),
        "",
        format_kv("Session", pool_id, ctx=ctx),
        format_kv("Started at", _format_timestamp(state.get("started_at")), ctx=ctx),
        format_kv("Piscine day", f"Day {day_number}" if isinstance(day_number, int) else day_number, ctx=ctx),
        format_kv("Elapsed", format_duration(started_elapsed), ctx=ctx),
        "",
        render_separator("Current", ctx=ctx),
        "",
        format_kv("Module", f"{info['module']} ({module_id})", ctx=ctx),
        format_kv("Exercise", info["exercise_id"], ctx=ctx),
        format_kv("Subject", current, ctx=ctx),
        format_kv("Reason", info["reason"], ctx=ctx),
        format_kv("Next", info["next_subject_id"], ctx=ctx),
        "",
        render_separator("Progress", ctx=ctx),
        "",
        format_kv("Overall", render_progress_bar(len(completed), len(selected)), ctx=ctx),
        format_kv("Current module", render_progress_bar(module_done, len(module_subjects), width=10), ctx=ctx),
        "",
        summarize_module_progress(repo, root, state, ctx),
        "",
        render_separator("Last Moulinette", ctx=ctx),
        "",
        format_kv("Status", last_status, ctx=ctx),
        format_kv("Reason", last_reason, ctx=ctx),
        format_kv("Attempts", attempts, ctx=ctx),
        format_kv("Trace", trace_path, ctx=ctx, role="path"),
        "",
        render_separator("Paths", ctx=ctx),
        "",
        format_kv("Subject", _rel(root, _subject_path(root)), ctx=ctx, role="path"),
        format_kv("Rendu", _rel(root, _rendu_path(root)) + "/", ctx=ctx, role="path"),
    ]
    return "\n".join(lines)


def summarize_exam(repo, root: Path, progress: dict, state: dict, ctx: RenderContext | None = None) -> str:
    if not state.get("pool_id"):
        return "No active exam session."
    return render_exam_status(repo, root, progress, state, ctx=ctx)


def summarize_progress(repo, root: Path, session_state: dict | None = None, ctx: RenderContext | None = None) -> str:
    state = session_state or {}
    if not state:
        return "No active session."
    progress = load_progress(root)
    if _mode(state) == "exam":
        return summarize_exam(repo, root, progress, state, ctx)
    return summarize_curriculum(repo, root, progress, state, ctx)


def summarize_history(
    repo,
    root: Path,
    session_state: dict | None = None,
    view: str = "all",
    ctx: RenderContext | None = None,
) -> str:
    del repo
    state = session_state or {}
    data = load_progress(root)
    attempts = data.get("attempt_log", [])
    counts = Counter(item.get("subject_id") for item in attempts if item.get("subject_id"))
    failures_by_subject: dict[str, list[dict]] = defaultdict(list)
    completed = set()
    for pool_entry in data.get("curricula", {}).values():
        completed.update(pool_entry.get("completed", []))
    for exam_entry in data.get("exams", {}).values():
        for item in exam_entry.get("picked", []):
            if item.get("status") == "OK":
                completed.add(item.get("subject_id"))
    for item in attempts:
        if item.get("status") != "OK":
            failures_by_subject[item.get("subject_id")].append(item)

    title_map = {
        "all": "Progress History",
        "failed": "Failed Exercises",
        "completed": "Completed Exercises",
        "attempts": "Exercise Attempts",
    }
    title = title_map.get(view, "Progress History")
    lines = [render_separator(title, ctx=ctx), ""]

    if view in {"all", "completed"}:
        lines.append("Completed")
        if completed:
            for subject_id in sorted(sid for sid in completed if sid):
                lines.append(f"  {status_marker('OK', ctx)} {subject_id}")
        else:
            lines.append("  - none")
        lines.append("")

    if view in {"all", "failed"}:
        lines.append("Failed")
        if failures_by_subject:
            for subject_id in sorted(failures_by_subject):
                last = failures_by_subject[subject_id][-1]
                lines.append(
                    f"  {status_marker('KO', ctx)} {subject_id:<24} "
                    f"attempts: {len(failures_by_subject[subject_id]):<3} "
                    f"reason: {last.get('reason') or 'unknown'}"
                )
        else:
            lines.append("  - none")
        lines.append("")

    if view in {"all", "attempts"}:
        lines.append("Attempts")
        if counts:
            for subject_id in sorted(counts):
                subject_attempts = [item for item in attempts if item.get("subject_id") == subject_id]
                last = subject_attempts[-1]
                spent = last.get("time_spent_seconds")
                time_text = format_duration(spent) if spent is not None else "not available"
                lines.append(
                    f"  {status_marker(last.get('status'), ctx)} {subject_id:<24} "
                    f"attempts: {counts[subject_id]:<3} time: {time_text} "
                    f"trace: {last.get('trace', 'none')}"
                )
        else:
            lines.append("  - none")
        lines.append("")

    lines.append("Resume")
    if state:
        lines.append(f"  Correction: {correction_label(state)}")
    lines.append(f"  Next: {next_subject_id(state) or current_subject_id(state) or 'none'}")
    return "\n".join(lines).rstrip()
