from __future__ import annotations

from typing import Any


def module_label(module_id: object | None) -> str:
    raw = str(module_id or "unknown")
    lower = raw.lower()
    if lower.startswith("shell") and lower[5:].isdigit():
        return f"Shell{int(lower[5:]):02d}"
    if lower.startswith("c") and lower[1:].isdigit():
        return f"C{int(lower[1:]):02d}"
    if lower == "projects":
        return "Projects"
    return raw.replace("_", " ").title()


def exercise_label(index: object | None) -> str:
    try:
        value = int(index)
    except (TypeError, ValueError):
        return "unknown"
    return f"ex{value:02d}"


def pool_display_name(pool_id: str, pool: dict[str, Any] | None = None) -> str:
    pool = pool or {}
    if pool.get("display_name"):
        return str(pool["display_name"])
    if "piscine42" in pool_id:
        return "Piscine42"
    return pool_id


def exam_display_name(pool_id: str, pool: dict[str, Any] | None = None) -> str:
    pool = pool or {}
    return str(pool.get("display_name") or pool_id)


def current_item(state: dict[str, Any] | None) -> dict[str, Any]:
    state = state or {}
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0) or 0)
    if selected and 0 <= index < len(selected):
        return selected[index]
    return {}


def next_item(state: dict[str, Any] | None) -> dict[str, Any]:
    state = state or {}
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0) or 0)
    if selected and index + 1 < len(selected):
        return selected[index + 1]
    return {}


def module_subjects(pool: dict[str, Any], module_id: object | None) -> list[str]:
    target = str(module_id or "")
    for module in pool.get("modules", []) or []:
        if str(module.get("id")) == target:
            return [str(sid) for sid in module.get("subjects", []) or []]
    return []


def curriculum_modules(pool: dict[str, Any]) -> list[dict[str, Any]]:
    return list(pool.get("modules", []) or [])


def module_position(pool: dict[str, Any], module_id: object | None) -> tuple[int, int]:
    modules = curriculum_modules(pool)
    target = str(module_id or "")
    for index, module in enumerate(modules, start=1):
        if str(module.get("id")) == target:
            return index, len(modules)
    return 0, len(modules)


def subject_context_from_pool(pool: dict[str, Any], subject_id: str) -> dict[str, Any]:
    for module in curriculum_modules(pool):
        subjects = [str(sid) for sid in module.get("subjects", []) or []]
        if subject_id in subjects:
            index = subjects.index(subject_id)
            return {
                "module_id": module.get("id"),
                "module": module_label(module.get("id")),
                "exercise_id": exercise_label(index),
                "exercise_index": index,
                "module_total": len(subjects),
            }
    return {
        "module_id": "unknown",
        "module": "unknown",
        "exercise_id": "unknown",
        "exercise_index": None,
        "module_total": 0,
    }


def current_curriculum_context(repo, state: dict[str, Any], progress: dict[str, Any] | None = None) -> dict[str, Any]:
    pool_id = str(state.get("pool_id") or "none")
    try:
        pool = repo.get_pool(pool_id)
    except SystemExit:
        pool = {"modules": []}
    item = current_item(state)
    subject_id = str(item.get("subject_id") or "none")
    module_id = item.get("module") or state.get("module_id")
    subjects = module_subjects(pool, module_id)
    index = item.get("index")
    if index is None and subject_id in subjects:
        index = subjects.index(subject_id)
    next_subject = str(next_item(state).get("subject_id") or "none")
    module_done = 0
    reason = str(state.get("selection_reason") or "")
    if progress:
        entry = progress.get("curricula", {}).get(pool_id, {})
        completed = set(entry.get("completed", []) or [])
        module_done = len([sid for sid in subjects if sid in completed])
        if not reason:
            if completed:
                reason = "previous exercises completed"
            elif int(state.get("current_index", 0) or 0) == 0:
                reason = "first exercise in module"
    if not reason:
        reason = "selected exercise"
    pos, total_modules = module_position(pool, module_id)
    return {
        "pool_id": pool_id,
        "pool": pool_display_name(pool_id, pool),
        "module_id": str(module_id or "unknown"),
        "module": module_label(module_id),
        "module_position": pos,
        "module_count": total_modules,
        "exercise_id": exercise_label(index),
        "exercise_index": index,
        "module_total": len(subjects),
        "module_done": module_done,
        "subject_id": subject_id,
        "next_subject_id": next_subject,
        "reason": reason,
    }


def exam_level_count(pool: dict[str, Any]) -> int:
    if pool.get("levels_count") is not None:
        return int(pool.get("levels_count") or 0)
    return len(pool.get("levels", []) or [])


def exam_context(repo, state: dict[str, Any]) -> dict[str, Any]:
    pool_id = str(state.get("pool_id") or "none")
    try:
        pool = repo.get_pool(pool_id)
    except SystemExit:
        pool = {}
    item = current_item(state)
    level = item.get("level", state.get("level"))
    try:
        level_number = int(level)
    except (TypeError, ValueError):
        level_number = None
    return {
        "pool_id": pool_id,
        "exam": exam_display_name(pool_id, pool),
        "group": str(pool.get("group") or "Exam"),
        "level": "unknown" if level is None else str(level),
        "level_position": (level_number + 1) if level_number is not None else 0,
        "level_count": exam_level_count(pool),
        "subject_id": str(item.get("subject_id") or "none"),
        "next_subject_id": str(next_item(state).get("subject_id") or "none"),
    }
