from __future__ import annotations

from pathlib import Path

from .failure_labels import moulinette_label_for
from .progress import current_module_id, current_subject_id, load_progress
from .trace import latest_trace, trace_path, utc_timestamp, write_trace
from .ui import RenderContext, format_kv, render_separator


def _rel(root: Path, path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _module_for_state(repo, state: dict) -> tuple[str, dict, list[str]]:
    pool_id = state.get("pool_id")
    pool = repo.get_pool(pool_id) if pool_id else {"modules": []}
    module_id = current_module_id(state)
    selected = state.get("selected") or []
    if not module_id:
        current = current_subject_id(state)
        current_item = next((item for item in selected if item.get("subject_id") == current), {})
        module_id = current_item.get("module")
    subjects = [item.get("subject_id") for item in selected if item.get("module") == module_id]
    module_data = {}
    for module in pool.get("modules", []) or []:
        if module.get("id") == module_id:
            module_data = module
            if not subjects:
                subjects = list(module.get("subjects", []) or [])
            break
    return str(module_id or "unknown"), module_data, [sid for sid in subjects if sid]


def _result_for_subject(progress: dict, pool_id: str, subject_id: str) -> dict | None:
    curriculum = progress.get("curricula", {}).get(pool_id, {})
    completed = set(curriculum.get("completed", []) or [])
    failed = curriculum.get("failed", {}) or {}
    subject_result = progress.get("subjects", {}).get(subject_id, {}).get("last_result")
    if subject_id in completed:
        if subject_result and subject_result.get("pool_id") in {pool_id, None}:
            return subject_result
        return {"subject_id": subject_id, "status": "OK"}
    if subject_id in failed:
        if subject_result and subject_result.get("pool_id") in {pool_id, None}:
            return subject_result
        last = curriculum.get("last_result") or {}
        if last.get("subject_id") == subject_id:
            return last
        return {"subject_id": subject_id, "status": "KO"}
    return None


def build_module_summary(repo, root: Path, state: dict) -> dict:
    pool_id = state.get("pool_id")
    if not pool_id:
        raise ValueError("No active Piscine pool.")
    module_id, module_data, subjects = _module_for_state(repo, state)
    progress = load_progress(root)
    grading = module_data.get("grading", {}) if isinstance(module_data, dict) else {}
    strict = bool(grading.get("strict_order") or grading.get("stop_on_failure"))
    exercises = []
    blocked = False
    ok_count = 0
    for subject_id in subjects:
        result = None if blocked else _result_for_subject(progress, pool_id, subject_id)
        if blocked:
            label = "Not evaluated"
            status = "NOT_EVALUATED"
        elif result is None:
            label = "Pending"
            status = "PENDING"
        else:
            status = str(result.get("status", "KO"))
            label = moulinette_label_for(result)
            if status == "OK":
                ok_count += 1
            elif strict:
                blocked = True
        exercises.append(
            {
                "subject_id": subject_id,
                "status": status,
                "label": label,
                "failure_category": (result or {}).get("failure_category", ""),
                "trace": (result or {}).get("trace", ""),
            }
        )
    total = len(subjects)
    return {
        "type": "module_summary",
        "pool_id": pool_id,
        "module_id": module_id,
        "project": module_data.get("title") or f"{pool_id} {module_id}",
        "timestamp": utc_timestamp(),
        "score": None,
        "score_label": "not configured",
        "grading_policy": grading,
        "status": "OK" if total and ok_count == total else "KO",
        "exercises": exercises,
    }


def render_module_summary(
    repo,
    root: Path,
    state: dict,
    *,
    trace_file: Path | None = None,
    ctx: RenderContext | None = None,
) -> str:
    summary = build_module_summary(repo, root, state)
    trace = trace_file or latest_trace(root / "workspace" / "traces")
    lines = [
        render_separator("Moulinette Summary", ctx=ctx),
        "",
        format_kv("Project", summary["project"], ctx=ctx),
        format_kv("Result", f"[{summary['status']}]", ctx=ctx),
        format_kv("Score", summary["score_label"], ctx=ctx),
        "",
        render_separator("Exercises", ctx=ctx),
        "",
    ]
    label_width = max(15, *(len(str(exercise["subject_id"])) for exercise in summary["exercises"]))
    for item in summary["exercises"]:
        lines.append(format_kv(item["subject_id"], item["label"], width=label_width, ctx=ctx))
    lines.extend(["", render_separator("Trace", ctx=ctx), "", _rel(root, trace)])
    return "\n".join(lines)


def write_module_summary_trace(root: Path, summary: dict) -> Path:
    trace_dir = root / "workspace" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_path(trace_dir, {"timestamp": summary.get("timestamp"), "subject_id": f"module-{summary.get('module_id', 'summary')}"})
    write_trace(path, summary)
    write_trace(trace_dir / "module_summary.json", summary)
    return path
