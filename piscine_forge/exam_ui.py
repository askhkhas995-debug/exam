from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .curriculum import exam_context, exam_display_name, exam_level_count
from .trace import latest_trace
from .ui import RenderContext, format_duration, format_kv, render_progress_bar, render_separator, status_marker


EXAM_GROUP_ORDER = [
    "ExamShell-style Practice",
    "Rank Practice",
    "Handwritten Practice",
    "Imported Practice",
    "Legacy Practice",
]


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def elapsed_seconds(value: str | None, *, now: datetime | None = None) -> int | None:
    started = parse_time(value)
    if started is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, int((now - started).total_seconds()))


def format_started_time(value: str | None) -> str:
    parsed = parse_time(value)
    if parsed is None:
        return "not configured"
    return parsed.strftime("%H:%M")


def pool_duration_seconds(pool: dict[str, Any]) -> int | None:
    minutes = pool.get("duration_minutes")
    return int(minutes) * 60 if minutes is not None else None


def state_duration_seconds(state: dict[str, Any], pool: dict[str, Any] | None = None) -> int | None:
    if state.get("duration_seconds") is not None:
        return int(state["duration_seconds"])
    if state.get("duration_minutes") is not None:
        return int(state["duration_minutes"]) * 60
    if pool:
        return pool_duration_seconds(pool)
    return None


def exam_timer_rows(state: dict[str, Any], pool: dict[str, Any] | None = None, *, ctx: RenderContext | None = None) -> list[str]:
    duration = state_duration_seconds(state, pool)
    if duration is None:
        return [
            format_kv("Duration", "not configured", ctx=ctx),
            format_kv("Elapsed", "not configured", ctx=ctx),
            format_kv("Remaining", "not configured", ctx=ctx),
        ]
    elapsed = elapsed_seconds(state.get("started_at"))
    remaining = None if elapsed is None else max(0, duration - elapsed)
    return [
        format_kv("Started", format_started_time(state.get("started_at")), ctx=ctx),
        format_kv("Duration", format_duration(duration), ctx=ctx),
        format_kv("Elapsed", format_duration(elapsed), ctx=ctx),
        format_kv("Remaining", format_duration(remaining), ctx=ctx),
    ]


def render_exam_rules(*, ctx: RenderContext | None = None) -> str:
    return "\n".join(
        [
            render_separator("Exam Rules", ctx=ctx),
            "",
            "- Solve the current exercise in workspace/rendu/.",
            "- Run `pforge grademe` when ready.",
            "- [OK] unlocks the next level.",
            "- [KO] keeps you on the current level.",
            "- Use `pforge trace` to inspect failures.",
            "- Exam mode uses Grademe, not Moulinette.",
        ]
    )


def render_exam_levels(pool_id: str, pool: dict[str, Any], *, ctx: RenderContext | None = None) -> str:
    lines = [render_separator(exam_display_name(pool_id, pool), ctx=ctx), ""]
    for level in pool.get("levels", []) or []:
        assignments = level.get("assignments", []) or []
        lines.append(f"  Level {level.get('level')}  {len(assignments)} exercises available")
    if len(lines) == 2:
        lines.append("  No levels configured.")
    return "\n".join(lines)


def render_exam_setup(pool_id: str, pool: dict[str, Any], *, ctx: RenderContext | None = None) -> str:
    duration = pool_duration_seconds(pool)
    rows = [
        format_kv("Exam", exam_display_name(pool_id, pool), ctx=ctx),
        format_kv("Pool", pool_id, ctx=ctx),
        format_kv("Levels", exam_level_count(pool), ctx=ctx),
        format_kv("Timer", format_duration(duration) if duration is not None else "not configured", ctx=ctx),
        format_kv("Correction", "Grademe", ctx=ctx),
    ]
    lines = [
        render_separator("Exam Setup", ctx=ctx),
        "",
        *rows,
        "",
        "  1  Start exam",
        "  2  Start with seed",
        "  3  View levels",
        "  4  Rules",
        "  0  Back",
    ]
    return "\n".join(lines)


def _rel(root: Path, path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def render_exam_started(repo, state: dict[str, Any], *, ctx: RenderContext | None = None) -> str:
    info = exam_context(repo, state)
    seed = state.get("seed")
    lines = [
        render_separator("Exam Started", ctx=ctx),
        "",
        format_kv("Exam", info["exam"], ctx=ctx),
        format_kv("Pool", info["pool_id"], ctx=ctx),
        format_kv("Seed", seed if seed is not None else "random", ctx=ctx),
        format_kv("Level", f"{info['level']} / {info['level_count']}", ctx=ctx),
        format_kv("Exercise", info["subject_id"], ctx=ctx),
        format_kv("Correction", "Grademe", ctx=ctx),
        format_kv("Rendu", "workspace/rendu", ctx=ctx, role="path"),
        "",
        render_separator("Next", ctx=ctx),
        "",
        "Solve the exercise, then run `pforge grademe`.",
    ]
    return "\n".join(lines)


def render_exam_screen(repo, root: Path, state: dict[str, Any], *, ctx: RenderContext | None = None) -> str:
    pool = repo.get_pool(state["pool_id"])
    info = exam_context(repo, state)
    lines = [
        render_separator("Exam", ctx=ctx),
        "",
        format_kv("Exam", info["exam"], ctx=ctx),
        format_kv("Pool", info["pool_id"], ctx=ctx),
        format_kv("Level", f"{info['level']} / {info['level_count']}", ctx=ctx),
        format_kv("Exercise", info["subject_id"], ctx=ctx),
        format_kv("Correction", "Grademe", ctx=ctx),
        format_kv("Rendu", _rel(root, root / "workspace" / "rendu"), ctx=ctx, role="path"),
        "",
        render_separator("Timer", ctx=ctx),
        "",
        *exam_timer_rows(state, pool, ctx=ctx),
        "",
        render_separator("Instructions", ctx=ctx),
        "",
        "Solve the current exercise in workspace/rendu/.",
        "Run `pforge grademe` when ready.",
        "[OK] unlocks the next level.",
        "[KO] keeps you on the current level.",
        "",
        render_separator("Actions", ctx=ctx),
        "",
        "  1  Open subject",
        "  2  Run Grademe",
        "  3  Trace",
        "  4  Exam status",
        "  5  Exam rules",
        "  0  Back",
    ]
    return "\n".join(lines)


def render_exam_status(repo, root: Path, progress: dict[str, Any], state: dict[str, Any], *, ctx: RenderContext | None = None) -> str:
    pool_id = state.get("pool_id")
    pool = repo.get_pool(pool_id)
    info = exam_context(repo, state)
    key = f"{pool_id}:{state.get('seed') if state.get('seed') is not None else 'none'}"
    entry = progress.get("exams", {}).get(key, {})
    picked = entry.get("picked") or state.get("selected", [])
    current_subject = info["subject_id"]
    last = entry.get("last_result")
    trace = last.get("trace") if last else _rel(root, latest_trace(root / "workspace" / "traces"))
    solved = len([item for item in picked if item.get("status") == "OK"])
    lines = [
        render_separator("Exam Status", ctx=ctx),
        "",
        format_kv("Exam", info["exam"], ctx=ctx),
        format_kv("Pool", pool_id, ctx=ctx),
        format_kv("Seed", state.get("seed") if state.get("seed") is not None else "random", ctx=ctx),
        format_kv("Level", f"{info['level']} / {info['level_count']}", ctx=ctx),
        format_kv("Exercise", current_subject, ctx=ctx),
        format_kv("Correction", "Grademe", ctx=ctx),
        "",
        render_separator("Progress", ctx=ctx),
        "",
    ]
    for item in picked:
        level = item.get("level")
        level_text = "?" if level is None else str(level)
        subject = item.get("subject_id", "pending")
        status = item.get("status")
        if subject == current_subject:
            marker = "[>]"
        elif status == "OK":
            marker = status_marker("OK", ctx)
        elif status == "KO":
            marker = status_marker("KO", ctx)
        else:
            marker = "[ ]"
        lines.append(f"{marker}  level {level_text:<2} {subject}")
    if not picked:
        lines.append("[ ]  no levels selected")
    lines.extend(
        [
            "",
            format_kv("Solved", render_progress_bar(solved, len(picked)), ctx=ctx),
            "",
            render_separator("Timer", ctx=ctx),
            "",
            *exam_timer_rows(state, pool, ctx=ctx),
            "",
            render_separator("Last Grademe", ctx=ctx),
            "",
        ]
    )
    if last:
        lines.extend(
            [
                format_kv("Status", status_marker(last.get("status"), ctx), ctx=ctx),
                format_kv("Reason", last.get("failure_reason") or last.get("reason") or "none", ctx=ctx),
            ]
        )
    else:
        lines.append(format_kv("Status", "none", ctx=ctx))
    lines.append(format_kv("Trace", trace, ctx=ctx, role="path"))
    return "\n".join(lines)
