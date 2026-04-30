from __future__ import annotations

from piscine_forge.loader import Repository
from piscine_forge.session import Session

from . import c_function, c_program, project, shell


DISPATCH = {
    "c_program": c_program.evaluate,
    "c_function": c_function.evaluate,
    "shell": shell.evaluate,
    "project": project.evaluate,
}


def evaluate_subject(repo: Repository, session: Session, subject_id: str | None = None) -> dict:
    sid = subject_id or session.current_subject_id()
    subject = repo.get_subject(sid)
    evaluator = repo.correction_profile(subject).get("evaluator") or subject["meta"].get("type")
    if evaluator not in DISPATCH:
        raise SystemExit(f"Unsupported evaluator {evaluator!r} for subject {sid}")
    return DISPATCH[evaluator](repo, session, subject)
