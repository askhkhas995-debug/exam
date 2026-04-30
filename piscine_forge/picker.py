from __future__ import annotations

import random

from .curriculum import exercise_label


def pick_from_pool(pool: dict, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    picked = []
    for level in pool.get("levels", []):
        assignments = list(level.get("assignments", []))
        count = int(level.get("pick", 1))
        if not assignments:
            continue
        for sid in rng.sample(assignments, min(count, len(assignments))):
            picked.append({"level": level.get("level"), "subject_id": sid})
    return picked


def curriculum_sequence(pool: dict) -> list[dict]:
    picked = []
    for module in pool.get("modules", []):
        for index, sid in enumerate(module.get("subjects", [])):
            picked.append(
                {
                    "module": module.get("id"),
                    "index": index,
                    "exercise_id": exercise_label(index),
                    "subject_id": sid,
                }
            )
    return picked
