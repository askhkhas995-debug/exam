from __future__ import annotations

from pathlib import Path
import json
import shutil

from .loader import Repository, dump_yaml
from .trace import utc_timestamp


PRIVATE_SUBJECT_NAMES = {
    "tests.yml",
    "test.yml",
    "private_tests.yml",
    "profile.yml",
    "hidden_main.c",
    "__hidden_main.c",
    "corrections",
    "private",
    "__pycache__",
}


def _parse_utc_timestamp(value: str | None):
    if not value:
        return None
    from datetime import datetime, timezone

    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _elapsed_seconds_since(value: str | None) -> int:
    from datetime import datetime, timezone

    started = _parse_utc_timestamp(value)
    if started is None:
        return 0
    return max(0, int((datetime.now(timezone.utc) - started).total_seconds()))


class Session:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.workspace = self.root / "workspace"
        self.subject_dir = self.workspace / "subject"
        self.rendu_dir = self.workspace / "rendu"
        self.trace_dir = self.workspace / "traces"
        self.state_path = self.workspace / "session.json"

    def ensure(self) -> None:
        for path in [self.subject_dir, self.rendu_dir, self.trace_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def clear_subject(self) -> None:
        if self.subject_dir.exists():
            shutil.rmtree(self.subject_dir)
        self.subject_dir.mkdir(parents=True, exist_ok=True)

    def clear_rendu(self) -> None:
        if self.rendu_dir.exists():
            shutil.rmtree(self.rendu_dir)
        self.rendu_dir.mkdir(parents=True, exist_ok=True)

    def clear_traces(self) -> None:
        if self.trace_dir.exists():
            shutil.rmtree(self.trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def reset(self, *, clear_rendu: bool = True) -> None:
        self.clear_subject()
        if clear_rendu:
            self.clear_rendu()
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not self.state_path.exists():
            raise SystemExit("No active session. Run `pforge start ...` or `pforge exam ...` first.")
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def load_if_exists(self) -> dict:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save(self, state: dict) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = utc_timestamp()
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def start(
        self,
        repo: Repository,
        *,
        pool_id: str,
        kind: str,
        selected: list[dict],
        seed: int | None = None,
        subject_id: str | None = None,
        current_index: int | None = None,
        duration_seconds: int | None = None,
        selection_reason: str | None = None,
    ) -> dict:
        self.ensure()
        self.reset(clear_rendu=True)
        selected_index = int(current_index or 0)
        if subject_id:
            for index, item in enumerate(selected):
                if item.get("subject_id") == subject_id:
                    selected_index = index
                    break
            else:
                selected_item: dict[str, object] = {"subject_id": subject_id}
                if kind == "exam":
                    pool = repo.get_pool(pool_id)
                    target_level = None
                    for level in pool.get("levels", []) or []:
                        level_value = level.get("level")
                        assignments = level.get("assignments", []) or []
                        for assignment in assignments:
                            assignment_subject = assignment.get("subject_id") if isinstance(assignment, dict) else assignment
                            if assignment_subject == subject_id:
                                selected_item["level"] = level_value
                                target_level = level_value
                                break
                        if selected_item.get("level") is not None:
                            break
                    if target_level is not None:
                        rebuilt: list[dict[str, object]] = []
                        for level in pool.get("levels", []) or []:
                            level_value = level.get("level")
                            level_selected = [item for item in selected if item.get("level") == level_value]
                            if level_value == target_level:
                                rebuilt.append({"subject_id": subject_id, "level": level_value})
                                continue
                            if level_selected:
                                rebuilt.extend(level_selected)
                                continue
                            assignments = level.get("assignments", []) or []
                            if assignments:
                                first = assignments[0]
                                first_subject = first.get("subject_id") if isinstance(first, dict) else first
                                rebuilt.append({"subject_id": first_subject, "level": level_value})
                        selected = rebuilt or [selected_item]
                        selected_index = next(
                            (i for i, item in enumerate(selected) if item.get("subject_id") == subject_id),
                            0,
                        )
                    else:
                        selected = [selected_item]
                        selected_index = 0
                else:
                    selected = [selected_item]
                    selected_index = 0
        if selected and not (0 <= selected_index < len(selected)):
            selected_index = 0
        if not selected:
            raise SystemExit(f"Pool {pool_id} has no selectable subjects")
        now = utc_timestamp()
        current = selected[selected_index]
        mode = "exam" if kind == "exam" else "curriculum"
        state = {
            "pool_id": pool_id,
            "kind": kind,
            "mode": mode,
            "seed": seed,
            "current_index": selected_index,
            "selected": selected,
            "completed": [],
            "started_at": now,
            "current_exercise_started_at": now,
            "time_spent_by_subject": {},
        }
        if selection_reason:
            state["selection_reason"] = selection_reason
        if current.get("module") is not None:
            state["module_id"] = current.get("module")
        if current.get("level") is not None:
            state["level"] = current.get("level")
        if duration_seconds is not None:
            state["duration_seconds"] = int(duration_seconds)
            state["duration_minutes"] = int(duration_seconds) // 60
        self.save(state)
        self.prepare_current_subject(repo)
        return self.load()

    def current_subject_id(self) -> str:
        state = self.load()
        return state["selected"][state["current_index"]]["subject_id"]

    def set_current_subject(self, repo: Repository, subject_id: str) -> None:
        repo.get_subject(subject_id)
        state = self.load() if self.state_path.exists() else {
            "pool_id": "manual",
            "kind": "manual",
            "mode": "exercise",
            "seed": None,
            "current_index": 0,
            "selected": [],
            "completed": [],
            "started_at": utc_timestamp(),
            "current_exercise_started_at": utc_timestamp(),
            "time_spent_by_subject": {},
        }
        state["selected"] = [{"subject_id": subject_id}]
        state["current_index"] = 0
        state["module_id"] = repo.get_subject(subject_id)["meta"].get("module")
        self.save(state)
        self.prepare_current_subject(repo)

    def prepare_current_subject(self, repo: Repository) -> None:
        self.ensure()
        self.clear_subject()

        subject_id = self.current_subject_id()
        entry = repo.get_subject(subject_id)
        if not entry.get("virtual"):
            for item in entry["path"].iterdir():
                if not self._is_student_visible(item):
                    continue
                target = self.subject_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
        else:
            (self.subject_dir / "subject.en.txt").write_text(repo.subject_text(subject_id), encoding="utf-8")

        public_meta = dict(entry["meta"])
        public_meta.pop("correction", None)
        public_meta.pop("private_tests", None)
        public_meta.pop("hidden_tests", None)
        (self.subject_dir / "meta.yml").write_text(dump_yaml(public_meta), encoding="utf-8")

    def _is_student_visible(self, item: Path) -> bool:
        if item.name in PRIVATE_SUBJECT_NAMES:
            return False
        if item.name.startswith("."):
            return False
        if item.is_dir() and item.name.lower() in {"tests", "private", "corrections"}:
            return False
        return True

    def advance_after_success(self, repo: Repository) -> bool:
        state = self.load()
        current = state["selected"][state["current_index"]]
        subject_id = current["subject_id"]
        state.setdefault("completed", []).append(current)
        current["status"] = "OK"
        spent = _elapsed_seconds_since(state.get("current_exercise_started_at"))
        by_subject = state.setdefault("time_spent_by_subject", {})
        by_subject[subject_id] = int(by_subject.get(subject_id, 0)) + spent
        if state["current_index"] + 1 >= len(state["selected"]):
            self.save(state)
            return False
        state["current_index"] += 1
        next_item = state["selected"][state["current_index"]]
        state["current_exercise_started_at"] = utc_timestamp()
        if next_item.get("module") is not None:
            state["module_id"] = next_item.get("module")
        else:
            state.pop("module_id", None)
        if next_item.get("level") is not None:
            state["level"] = next_item.get("level")
        else:
            state.pop("level", None)
        self.save(state)
        self.prepare_current_subject(repo)
        return True

    def finish(self) -> None:
        if self.state_path.exists():
            self.state_path.unlink()
        self.clear_subject()
