from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


REQUIRED_ROOT_DIRS = [
    "subjects",
    "corrections",
    "pools",
    "schemas",
    "piscine_forge",
    "workspace/subject",
    "workspace/rendu",
    "workspace/traces",
]


def load_yaml(path: Path):
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def dump_yaml(data: dict) -> str:
    if yaml is not None:
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    return json.dumps(data, indent=2, ensure_ascii=False)


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "subjects").exists():
            return candidate
    return current


def _infer_expected_file(subject_id: str, module: str, subject_type: str) -> str:
    if "." in subject_id:
        return subject_id
    if subject_type == "shell":
        return subject_id
    if subject_type == "project":
        return "Makefile"
    clean = subject_id.replace("-", "_")
    return f"{clean}.c"


def _infer_type(subject_id: str, module: str) -> str:
    if module.startswith("shell") or subject_id.endswith(".sh"):
        return "shell"
    if module == "projects" or subject_id in {"rush00", "rush01", "rush02", "sastantua", "bsq"}:
        return "project"
    return "c_function"


def _safe_title(subject_id: str) -> str:
    return re.sub(r"[_-]+", " ", subject_id).strip().title()


@dataclass
class Repository:
    root: Path

    def __post_init__(self) -> None:
        self.root = self.root.resolve()

    def config(self, name: str) -> dict:
        path = self.root / "config" / f"{name}.yml"
        return load_yaml(path) if path.exists() else {}

    def subjects(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for meta in sorted(self.root.glob("subjects/**/meta.yml")):
            data = load_yaml(meta)
            sid = data.get("id")
            if sid:
                out[sid] = {"path": meta.parent, "meta": data, "virtual": False}

        for index in sorted(self.root.glob("subjects/**/INDEX.yml")):
            data = load_yaml(index)
            module = str(data.get("module") or index.parent.name)
            origin = str(data.get("origin") or index.parent.parent.name)
            version = str(data.get("version") or "v0")
            submission_contracts = data.get("submission_contracts", {}) or {}
            for level, sid in enumerate(data.get("subjects", []) or []):
                if sid in out:
                    continue
                subject_type = _infer_type(str(sid), module)
                language = "sh" if subject_type == "shell" else "c"
                if subject_type == "project":
                    language = "c"
                expected = _infer_expected_file(str(sid), module, subject_type)
                out[str(sid)] = {
                    "path": index.parent / str(sid),
                    "meta": {
                        "id": str(sid),
                        "title": _safe_title(str(sid)),
                        "origin": origin,
                        "version": version,
                        "module": module,
                        "level": level,
                        "type": subject_type,
                        "language": language,
                        "expected_files": [expected],
                        "allowed_functions": ["write"] if language == "c" else [],
                        "forbidden_functions": ["printf", "puts", "fprintf"] if language == "c" else [],
                        "norminette": language == "c",
                        "tags": ["virtual-index"],
                    },
                    "virtual": True,
                    "index_path": index,
                }
                contract = submission_contracts.get(str(sid))
                if contract:
                    out[str(sid)]["meta"]["submission"] = contract
                
                correction = data.get("corrections", {}).get(str(sid))
                if correction:
                    out[str(sid)]["meta"]["correction"] = correction
        return out

    def pools(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for pool in sorted(self.root.glob("pools/**/*.yml")):
            data = load_yaml(pool)
            pid = data.get("id")
            if pid:
                out[pid] = {"path": pool, "pool": data}
        return out

    def get_subject(self, subject_id: str) -> dict:
        subjects = self.subjects()
        if subject_id not in subjects:
            raise SystemExit(f"Unknown subject: {subject_id}")
        return subjects[subject_id]

    def get_pool(self, pool_id: str) -> dict:
        pools = self.pools()
        if pool_id not in pools:
            raise SystemExit(f"Unknown pool: {pool_id}")
        return pools[pool_id]["pool"]

    def subject_text(self, subject_id: str, lang: str = "en") -> str:
        entry = self.get_subject(subject_id)
        path = entry["path"] / f"subject.{lang}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        meta = entry["meta"]
        return (
            f"# {meta['title']}\n\n"
            f"Origin: {meta.get('origin', 'unknown')}\n"
            f"Module: {meta.get('module', 'unknown')}\n"
            f"Type: {meta.get('type', 'unknown')}\n"
            f"Expected files: {', '.join(meta.get('expected_files', []))}\n\n"
            "This subject is indexed from the legacy/PDF handoff. Full text should be imported from the source archive.\n"
        )

    def tests_for_subject(self, subject: dict) -> dict:
        path = subject["path"] / "tests.yml"
        if path.exists():
            return load_yaml(path)
        profile = self.correction_profile(subject)
        tests_file = profile.get("fixed_tests_file")
        if tests_file and (self.root / tests_file).exists():
            return load_yaml(self.root / tests_file)
        return {"subject_id": subject["meta"]["id"], "fixed_tests": []}

    def correction_profile(self, subject: dict) -> dict:
        profile = subject["meta"].get("correction", {}).get("profile")
        if profile and (self.root / profile).exists():
            return load_yaml(self.root / profile)
        return {
            "subject_id": subject["meta"]["id"],
            "evaluator": subject["meta"].get("type"),
            "strict_stdout": True,
            "timeout_seconds": self.config("grading").get("grading", {}).get("timeout_seconds", 2),
        }

    def pool_subject_ids(self, pool: dict) -> list[str]:
        ids: list[str] = []
        for level in pool.get("levels", []) or []:
            ids.extend(str(sid) for sid in level.get("assignments", []) or [])
        for module in pool.get("modules", []) or []:
            ids.extend(str(sid) for sid in module.get("subjects", []) or [])
        return ids

    def validate(self) -> list[str]:
        errors: list[str] = []
        for rel in REQUIRED_ROOT_DIRS:
            if not (self.root / rel).exists():
                errors.append(f"missing required path: {rel}")

        subjects = self.subjects()
        for sid, entry in sorted(subjects.items()):
            meta = entry["meta"]
            for key in ["id", "title", "origin", "version", "type", "expected_files"]:
                if key not in meta:
                    errors.append(f"{sid}: missing {key}")
            if not entry.get("virtual") and not (entry["path"] / "subject.en.txt").exists():
                errors.append(f"{sid}: missing subject.en.txt")
            correction = meta.get("correction", {}).get("profile")
            if correction and not (self.root / correction).exists():
                errors.append(f"{sid}: missing correction profile {correction}")

        for pid, entry in sorted(self.pools().items()):
            pool = entry["pool"]
            for key in ["id", "kind"]:
                if key not in pool:
                    errors.append(f"pool {pid}: missing {key}")
            for sid in self.pool_subject_ids(pool):
                if sid not in subjects:
                    errors.append(f"pool {pid}: unknown subject {sid}")
        return errors
