from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from piscine_forge.interface import run_menu
from piscine_forge.loader import Repository
from piscine_forge.projects import discover_piscine_projects, render_project_list


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["python3", "-m", "piscine_forge.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=merged_env,
    )


def clean_workspace() -> None:
    workspace = ROOT / "workspace"
    for sub in ["rendu", "subject", "traces", "vogsphere"]:
        path = workspace / sub
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    for name in ["session.json", "progress.json"]:
        path = workspace / name
        if path.exists():
            path.unlink()


def test_project_discovery_is_limited_to_existing_piscine_projects() -> None:
    repo = Repository(ROOT)
    projects = discover_piscine_projects(repo)
    ids = [project["id"] for project in projects]

    assert ids == ["rush00", "rush01", "rush02", "sastantua", "match_n_match", "eval_expr", "bsq"]
    assert all(not subject_id.startswith("frog") for subject_id in ids)

    text = render_project_list(repo)
    assert "Piscine Projects" in text
    assert "Rush00" in text
    assert "BSQ" in text
    assert "Frog" not in text


def test_projects_command_and_menu_show_grouped_piscine_projects() -> None:
    clean_workspace()
    command = run_cli("projects")
    assert command.returncode == 0
    assert "Projects" in command.stdout
    assert "Piscine Projects" in command.stdout
    assert "Match-N-Match" in command.stdout
    assert "Frog" not in command.stdout

    repo = Repository(ROOT)
    output: list[str] = []
    answers = iter(["3", "0", "0"])
    result = run_menu(repo, input_func=lambda prompt="": next(answers), output=output.append)
    text = "\n".join(output)

    assert result == 0
    assert "Projects" in text
    assert "Piscine Projects" in text
    assert "Eval Expr" in text
    assert "Frog" not in text


def test_project_detail_handles_incomplete_requirements_honestly() -> None:
    clean_workspace()
    repo = Repository(ROOT)
    output: list[str] = []
    answers = iter(["3", "6", "2", "", "0", "0", "0"])
    result = run_menu(repo, input_func=lambda prompt="": next(answers), output=output.append)
    text = "\n".join(output)

    assert result == 0
    assert "Project" in text
    assert "Name           : Eval Expr" in text
    assert "Correction     : Project Moulinette" in text
    assert "Project Requirements" in text
    assert "metadata incomplete" in text
    assert "detailed submission requirements are not fully configured" in text


def test_project_requirements_commands_are_metadata_driven() -> None:
    repo = Repository(ROOT)
    ids = [project["id"] for project in discover_piscine_projects(repo)]
    for project_id in ids:
        result = run_cli("project", "requirements", project_id)
        assert result.returncode == 0
        assert "Project Requirements" in result.stdout
        assert "Project Moulinette" in result.stdout

    bsq = run_cli("project", "requirements", "bsq")
    assert "Project        : BSQ" in bsq.stdout
    assert "Status         : preflight configured" in bsq.stdout
    assert "Makefile" in bsq.stdout
    assert "Expected binary" in bsq.stdout
    assert "bsq" in bsq.stdout
    assert "corrections/*" in bsq.stdout
    assert "tests/*" in bsq.stdout

    rush = run_cli("project", "requirements", "rush00")
    assert "Project        : Rush00" in rush.stdout
    assert "rush_project" not in rush.stdout
    assert "Makefile" in rush.stdout
    assert "Expected binary" not in rush.stdout

    incomplete = run_cli("project", "requirements", "eval_expr")
    assert "Project        : Eval Expr" in incomplete.stdout
    assert "metadata incomplete" in incomplete.stdout
    assert "Cannot run strict submission check" not in incomplete.stdout


def test_project_current_reports_missing_active_project() -> None:
    clean_workspace()
    result = run_cli("project", "current")
    assert result.returncode == 1
    assert "No active project" in result.stdout


def test_project_check_empty_rendu_is_nothing_turned_in() -> None:
    clean_workspace()
    subject = ROOT / "workspace" / "subject"
    subject.mkdir(parents=True, exist_ok=True)
    (subject / "Makefile").write_text("not submitted\n", encoding="utf-8")

    result = run_cli("project", "check", "bsq")

    assert result.returncode == 0
    assert "Submission Check" in result.stdout
    assert "Project        : BSQ" in result.stdout
    assert "Status         : [KO]" in result.stdout
    assert "Nothing turned in" in result.stdout
    assert "workspace/subject" not in result.stdout


def test_project_check_detects_missing_required_and_binary() -> None:
    clean_workspace()
    rendu = ROOT / "workspace" / "rendu"
    rendu.mkdir(parents=True, exist_ok=True)
    (rendu / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")

    missing = run_cli("project", "check", "bsq")
    assert "required files : [KO]" in missing.stdout
    assert "Required file `Makefile` is missing." in missing.stdout

    (rendu / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    binary = run_cli("project", "check", "bsq")
    assert "required files : [OK]" in binary.stdout
    assert "makefile       : [OK]" in binary.stdout
    assert "binary         : [KO]" in binary.stdout
    assert "Expected binary `bsq` was not found after build." in binary.stdout

    (rendu / "bsq").write_text("#!/bin/sh\n", encoding="utf-8")
    ok = run_cli("project", "check", "bsq")
    assert "Status         : [OK]" in ok.stdout
    assert "binary         : [OK]" in ok.stdout


def test_project_check_reports_forbidden_files_without_exposing_contents() -> None:
    clean_workspace()
    rendu = ROOT / "workspace" / "rendu"
    rendu.mkdir(parents=True, exist_ok=True)
    (rendu / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    (rendu / "bsq").write_text("#!/bin/sh\n", encoding="utf-8")
    (rendu / "a.out").write_text("artifact\n", encoding="utf-8")
    (rendu / "tests").mkdir()
    (rendu / "tests" / "private.txt").write_text("secret fixture content\n", encoding="utf-8")

    result = run_cli("project", "check", "bsq")

    assert "forbidden files: [KO]" in result.stdout
    assert "Forbidden file found:" in result.stdout
    assert "secret fixture content" not in result.stdout


def test_project_check_incomplete_metadata_and_rush_ok_path() -> None:
    clean_workspace()
    incomplete = run_cli("project", "check", "eval_expr")
    assert incomplete.returncode == 0
    assert "metadata incomplete" in incomplete.stdout
    assert "Cannot run strict submission check yet." in incomplete.stdout

    rendu = ROOT / "workspace" / "rendu"
    rendu.mkdir(parents=True, exist_ok=True)
    (rendu / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    (rendu / "rush.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    rush = run_cli("project", "check", "rush00")
    assert "Project        : Rush00" in rush.stdout
    assert "Status         : [OK]" in rush.stdout
    assert "binary" not in rush.stdout


def test_project_check_rejects_unsafe_symlink() -> None:
    clean_workspace()
    target = ROOT / "workspace" / "rendu" / "leak"
    try:
        target.symlink_to(ROOT / "pyproject.toml")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    result = run_cli("project", "check", "bsq")

    assert "unsafe symlink rejected" in result.stdout


def test_project_check_does_not_use_vogsphere_submission() -> None:
    clean_workspace()
    rendu = ROOT / "workspace" / "rendu"
    rendu.mkdir(parents=True, exist_ok=True)
    (rendu / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    run_cli("vog", "init", "bsq")
    run_cli("vog", "commit", "-m", "snapshot", "bsq")
    run_cli("vog", "push", "bsq")
    assert (ROOT / "workspace" / "vogsphere" / "state.json").exists()

    shutil.rmtree(rendu)
    rendu.mkdir(parents=True, exist_ok=True)
    check = run_cli("project", "check", "bsq")

    assert "Nothing turned in" in check.stdout
    assert (ROOT / "workspace" / "vogsphere" / "state.json").exists()


def _write_sample_rendu() -> None:
    rendu = ROOT / "workspace" / "rendu"
    rendu.mkdir(parents=True, exist_ok=True)
    (rendu / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")


def test_vog_init_status_commit_log_push_submit_history_and_snapshot_safety(tmp_path: Path) -> None:
    clean_workspace()
    _write_sample_rendu()
    rendu = ROOT / "workspace" / "rendu"
    subject = ROOT / "workspace" / "subject"
    subject.mkdir(parents=True, exist_ok=True)
    (subject / "subject.en.txt").write_text("student-visible subject\n", encoding="utf-8")
    (subject / "tests.yml").write_text("private-ish workspace file\n", encoding="utf-8")

    (rendu / "a.out").write_text("ignored\n", encoding="utf-8")
    (rendu / "object.o").write_text("ignored\n", encoding="utf-8")
    (rendu / "program.out").write_text("ignored\n", encoding="utf-8")
    (rendu / ".DS_Store").write_text("ignored\n", encoding="utf-8")
    (rendu / "__pycache__").mkdir()
    (rendu / "__pycache__" / "x.pyc").write_bytes(b"ignored")
    (rendu / ".git").mkdir()
    (rendu / ".git" / "config").write_text("ignored\n", encoding="utf-8")

    home = tmp_path / "home"
    home.mkdir()
    env = {"HOME": str(home)}

    status_before = run_cli("vog", "status", "testrepo", env=env)
    assert status_before.returncode == 0
    assert "not initialized" in status_before.stdout

    init = run_cli("vog", "init", "testrepo", env=env)
    assert init.returncode == 0
    assert "Vogsphere Init" in init.stdout
    assert (ROOT / "workspace" / "vogsphere" / "state.json").exists()

    status_after = run_cli("vog", "status", "testrepo", env=env)
    assert status_after.returncode == 0
    assert "initialized" in status_after.stdout

    commit = run_cli("vog", "commit", "-m", "initial submit", "testrepo", env=env)
    assert commit.returncode == 0
    assert "Vogsphere Commit" in commit.stdout
    assert "initial submit" in commit.stdout

    state = json.loads((ROOT / "workspace" / "vogsphere" / "state.json").read_text(encoding="utf-8"))
    repo_state = state["repos"]["testrepo"]
    commit_id = repo_state["last_commit"]
    snapshot = ROOT / "workspace" / "vogsphere" / "repos" / "testrepo" / "commits" / commit_id

    assert (snapshot / "main.c").exists()
    assert not (snapshot / "a.out").exists()
    assert not (snapshot / "object.o").exists()
    assert not (snapshot / "program.out").exists()
    assert not (snapshot / ".DS_Store").exists()
    assert not (snapshot / "__pycache__").exists()
    assert not (snapshot / ".git").exists()
    assert not (snapshot / "subject.en.txt").exists()
    assert not (snapshot / "tests.yml").exists()
    assert not (snapshot / "corrections").exists()

    log = run_cli("vog", "log", "testrepo", env=env)
    assert log.returncode == 0
    assert commit_id in log.stdout
    assert "initial submit" in log.stdout

    push = run_cli("vog", "push", "testrepo", env=env)
    assert push.returncode == 0
    assert commit_id in push.stdout

    submit = run_cli("vog", "submit", "testrepo", env=env)
    assert submit.returncode == 0
    assert commit_id in submit.stdout

    history = run_cli("vog", "history", "testrepo", env=env)
    assert history.returncode == 0
    assert "init" in history.stdout
    assert "commit" in history.stdout
    assert "push" in history.stdout
    assert "submit" in history.stdout

    state = json.loads((ROOT / "workspace" / "vogsphere" / "state.json").read_text(encoding="utf-8"))
    assert state["repos"]["testrepo"]["last_push"] == commit_id
    assert state["repos"]["testrepo"]["submitted"] == commit_id
    assert not (home / ".ssh").exists()


def test_vog_rejects_unsafe_symlinks() -> None:
    clean_workspace()
    run_cli("vog", "init", "symlinkrepo")
    target = ROOT / "workspace" / "rendu" / "leak"
    try:
        target.symlink_to(ROOT / "pyproject.toml")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    result = run_cli("vog", "commit", "-m", "bad link", "symlinkrepo")

    assert result.returncode == 1
    assert "unsafe symlink rejected" in result.stdout
