from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess

from piscine_forge.interface import run_menu
from piscine_forge.loader import Repository


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "piscine_forge.cli", *args],
        cwd=ROOT,
        text=True,
        input=input_text,
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


def test_current_without_active_session() -> None:
    clean_workspace()
    result = run_cli("current")
    assert result.returncode == 0
    assert "No active session." in result.stdout
    assert "pforge start piscine42" in result.stdout


def test_current_after_start_shows_paths_and_next_subject() -> None:
    clean_workspace()
    start = run_cli("start", "piscine42", "--subject", "ft_print_numbers")
    assert start.returncode == 0
    current = run_cli("current")
    assert current.returncode == 0
    assert "Current Subject" in current.stdout
    assert "Mode           : Piscine" in current.stdout
    assert "Correction     : Moulinette" in current.stdout
    assert "Pool           : piscine42_default" in current.stdout
    assert "Subject        : ft_print_numbers" in current.stdout
    assert "workspace/subject/subject.en.txt" in current.stdout
    assert "workspace/rendu/" in current.stdout


def test_workspace_subject_contains_only_public_material() -> None:
    clean_workspace()
    result = run_cli("start", "piscine42", "--subject", "ft_print_comb")
    assert result.returncode == 0
    subject_dir = ROOT / "workspace" / "subject"
    copied = {path.name for path in subject_dir.iterdir()}
    assert "subject.en.txt" in copied
    assert "meta.yml" in copied
    assert "tests.yml" not in copied
    assert "profile.yml" not in copied
    assert "hidden_main.c" not in copied
    assert "__hidden_main.c" not in copied
    for path in subject_dir.rglob("*"):
        assert "corrections" not in path.parts
        assert "private" not in path.parts
    meta_text = (subject_dir / "meta.yml").read_text(encoding="utf-8")
    assert "corrections/" not in meta_text
    assert "profile:" not in meta_text


def test_reset_commands_are_workspace_scoped_and_keep_rendu() -> None:
    clean_workspace()
    assert run_cli("start", "piscine42", "--subject", "ft_print_numbers").returncode == 0
    workspace = ROOT / "workspace"
    (workspace / "progress.json").write_text(json.dumps({"version": 2}), encoding="utf-8")
    (workspace / "traces" / "sample.json").write_text("{}", encoding="utf-8")
    (workspace / "rendu" / "student_solution.c").write_text("int x;\n", encoding="utf-8")

    protected_paths = [
        ROOT / "subjects",
        ROOT / "corrections",
        ROOT / "pools",
        ROOT / "config",
        ROOT / "piscine_forge",
        ROOT / "tests",
        ROOT / "corrections" / "exams" / "handwritten_v5" / "print_nth_char" / "hidden_main.c",
    ]
    before = {path: path.exists() for path in protected_paths}

    session_reset = run_cli("reset", "session", "--yes")
    assert session_reset.returncode == 0
    assert not (workspace / "session.json").exists()
    assert (workspace / "progress.json").exists()
    assert (workspace / "traces" / "sample.json").exists()
    assert (workspace / "rendu" / "student_solution.c").exists()

    progress_reset = run_cli("reset", "progress", "--yes")
    assert progress_reset.returncode == 0
    assert not (workspace / "progress.json").exists()

    traces_reset = run_cli("reset", "traces", "--yes")
    assert traces_reset.returncode == 0
    assert not (workspace / "traces" / "sample.json").exists()
    assert (workspace / "rendu" / "student_solution.c").exists()

    all_reset = run_cli("reset", "all", "--yes")
    assert all_reset.returncode == 0
    assert (workspace / "rendu" / "student_solution.c").exists()
    assert before == {path: path.exists() for path in protected_paths}


def test_reset_requires_confirmation_for_progress_and_traces() -> None:
    clean_workspace()
    (ROOT / "workspace" / "progress.json").write_text("{}", encoding="utf-8")
    result = run_cli("reset", "progress", input_text="no\n")
    assert result.returncode == 1
    assert "Reset cancelled." in result.stdout
    assert (ROOT / "workspace" / "progress.json").exists()


def test_history_records_failed_attempt() -> None:
    clean_workspace()
    result = run_cli("grademe", "--subject", "alpha_index_case")
    assert result.returncode == 1
    history = run_cli("history", "failed")
    assert history.returncode == 0
    assert "Failed Exercises" in history.stdout
    assert "alpha_index_case" in history.stdout
    attempts = run_cli("history", "attempts")
    assert "alpha_index_case" in attempts.stdout


def test_exam_status_uses_configured_timer() -> None:
    clean_workspace()
    result = run_cli("exam", "handwritten_v5", "--seed", "42")
    assert result.returncode == 0
    status = run_cli("status")
    assert status.returncode == 0
    assert "Exam Status" in status.stdout
    assert "Duration       : 4 hours" in status.stdout
    assert "Remaining      :" in status.stdout
    assert "Remaining      : not configured" not in status.stdout
    assert "Elapsed        :" in status.stdout


def test_menu_is_injectable_and_exits() -> None:
    repo = Repository(ROOT)
    output: list[str] = []
    result = run_menu(repo, input_func=lambda prompt="": "0", output=output.append)
    assert result == 0
    assert any("PiscineForge" in line for line in output)
