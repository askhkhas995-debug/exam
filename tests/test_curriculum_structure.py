from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from piscine_forge.interface import browse_exercises, run_menu
from piscine_forge.loader import Repository


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "piscine_forge.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def clean_workspace() -> None:
    workspace = ROOT / "workspace"
    for sub in ["rendu", "subject", "traces"]:
        path = workspace / sub
        path.mkdir(parents=True, exist_ok=True)
        for item in list(path.iterdir()):
            if item.name == ".gitkeep":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    for name in ["session.json", "progress.json"]:
        path = workspace / name
        if path.exists():
            path.unlink()


def test_piscine42_explicit_order_and_subject_metadata() -> None:
    repo = Repository(ROOT)
    subjects = repo.subjects()
    pool = repo.get_pool("piscine42_default")

    assert "z" in subjects
    assert subjects["z"]["meta"]["module"] == "shell00"
    assert subjects["z"]["meta"]["level"] == 0
    assert "ft_putchar" in subjects
    assert subjects["ft_putchar"]["meta"]["module"] == "c00"
    assert subjects["ft_putchar"]["meta"]["level"] == 0

    modules = pool["modules"]
    assert [module["id"] for module in modules[:3]] == ["shell00", "shell01", "c00"]
    assert modules[0]["subjects"][0] == "z"
    assert modules[2]["subjects"][:4] == [
        "ft_putchar",
        "ft_print_alphabet",
        "ft_print_reverse_alphabet",
        "ft_print_numbers",
    ]


def test_clean_piscine_start_shows_shell00_ex00_context() -> None:
    clean_workspace()
    assert run_cli("reset", "session", "--yes").returncode == 0
    assert run_cli("reset", "progress", "--yes").returncode == 0

    start = run_cli("start", "piscine42")
    assert start.returncode == 0
    assert "module: Shell00 (shell00)" in start.stdout
    assert "exercise: ex00" in start.stdout
    assert "subject: z" in start.stdout
    assert "reason: first exercise in module" in start.stdout

    current = run_cli("current")
    assert "Pool           : piscine42_default" in current.stdout
    assert "Module         : Shell00 (shell00)" in current.stdout
    assert "Exercise       : ex00" in current.stdout
    assert "Subject        : z" in current.stdout
    assert "Next           : testShell00" in current.stdout


def test_resume_skips_only_completed_curriculum_subjects() -> None:
    clean_workspace()
    progress = {
        "version": 2,
        "curricula": {
            "piscine42_default": {
                "pool_id": "piscine42_default",
                "completed": ["z"],
                "failed": {},
                "last_result": None,
            }
        },
        "exams": {},
        "subjects": {},
        "attempt_log": [],
    }
    (ROOT / "workspace" / "progress.json").write_text(json.dumps(progress), encoding="utf-8")

    repo = Repository(ROOT)
    output: list[str] = []
    answers = iter(["1", "2", "1", "", "0"])
    result = run_menu(repo, input_func=lambda prompt="": next(answers), output=output.append)
    text = "\n".join(output)

    assert result == 0
    assert "Started piscine42_default: Shell00/ex01 testShell00" in text
    assert "Reason: previous exercises completed" in text


def test_piscine_menu_exposes_modules_before_exercises() -> None:
    clean_workspace()
    repo = Repository(ROOT)
    output: list[str] = []
    answers = iter(["1", "2", "3", "3", "0", "0", "0", "0"])
    result = run_menu(repo, input_func=lambda prompt="": next(answers), output=output.append)
    text = "\n".join(output)

    assert result == 0
    assert "Piscine42 (piscine42_default)" in text
    assert "Resume progress" in text
    assert "Browse modules" in text
    assert "Shell00" in text
    assert "C00" in text
    assert "ex00 ft_putchar" in text
    assert "ex03 ft_print_numbers" in text


def test_module_progress_command_lists_current_module() -> None:
    clean_workspace()
    assert run_cli("start", "piscine42", "--subject", "ft_print_numbers").returncode == 0

    progress = run_cli("module", "progress")

    assert progress.returncode == 0
    assert "C00 Progress" in progress.stdout
    assert "ex00  ft_putchar" in progress.stdout
    assert "ex03  ft_print_numbers" in progress.stdout
    assert "current" in progress.stdout


def test_exam_header_shows_group_exam_level_and_correction() -> None:
    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--seed", "42", "--subject", "first_last_char").returncode == 0
    repo = Repository(ROOT)
    output: list[str] = []
    result = run_menu(repo, input_func=lambda prompt="": "0", output=output.append)
    text = "\n".join(output)

    assert result == 0
    assert "Mode          : Exam" in text
    assert "Exam          : Handwritten Practice v5 (handwritten_v5)" in text
    assert "Level" in text and "0 / 5" in text
    assert "Exercise      : first_last_char" in text
    assert "Correction    : Grademe" in text


def test_browse_exercises_is_hierarchical() -> None:
    clean_workspace()
    repo = Repository(ROOT)
    output: list[str] = []
    browse_exercises(repo, session=type("DummySession", (), {})(), input_func=lambda prompt="": "0", output=output.append)
    text = "\n".join(output)

    assert "By Piscine module" in text
    assert "By Exam group" in text
    assert "Search by name" in text
    assert "Filter by type" in text
