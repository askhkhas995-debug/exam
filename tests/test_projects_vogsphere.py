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
INCOMPLETE_PROJECTS = {
    "sastantua": "Sastantua",
    "match_n_match": "Match-N-Match",
}
REMOTE_FETCH_TOKENS = (
    "requests",
    "urllib",
    "urlopen",
    "httpx",
    "socket",
    "curl",
    "wget",
    "git clone",
)


def assert_no_remote_fetches() -> None:
    checked_files = [
        ROOT / "piscine_forge" / "projects.py",
        ROOT / "piscine_forge" / "cli.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)
    for token in REMOTE_FETCH_TOKENS:
        assert token not in combined


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
    answers = iter(["3", "4", "2", "", "0", "0", "0"])
    result = run_menu(repo, input_func=lambda prompt="": next(answers), output=output.append)
    text = "\n".join(output)

    assert result == 0
    assert "Project" in text
    assert "Name           : Sastantua" in text
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
    assert "Project        : bsq" in bsq.stdout
    assert "Mode           : local trainer" in bsq.stdout
    assert "Correction status: local trainer" in bsq.stdout
    assert "Submission contract: configured" in bsq.stdout
    assert "Official 42 services: not connected" in bsq.stdout
    assert "Remote downloads: disabled" in bsq.stdout
    assert "Makefile" in bsq.stdout
    assert "Expected binary" in bsq.stdout
    assert "bsq" in bsq.stdout
    assert "corrections/*" in bsq.stdout
    assert "tests/*" in bsq.stdout

    rush = run_cli("project", "requirements", "rush00")
    assert "Project        : rush00" in rush.stdout
    assert "Correction status: local trainer" in rush.stdout
    assert "rush_project" not in rush.stdout
    assert "Makefile" in rush.stdout
    assert "Expected binary" in rush.stdout
    assert "rush-00" in rush.stdout

    for rush_id in ["rush01", "rush02"]:
        req = run_cli("project", "requirements", rush_id)
        assert f"Project        : {rush_id}" in req.stdout
        assert "Correction status: preflight only" in req.stdout
        assert "Submission contract: configured" in req.stdout
        assert "Local tests    : missing" in req.stdout
        assert "Project Moulinette is a local trainer, not official 42 Moulinette." in req.stdout


    eval_expr = run_cli("project", "requirements", "eval_expr")
    assert "Project        : eval_expr" in eval_expr.stdout
    assert "Correction status: local trainer" in eval_expr.stdout
    assert "Local tests    : configured" in eval_expr.stdout
    assert "Expected binary" in eval_expr.stdout
    assert "eval_expr" in eval_expr.stdout

    for project_id in INCOMPLETE_PROJECTS:
        incomplete = run_cli("project", "requirements", project_id)
        assert f"Project        : {project_id}" in incomplete.stdout
        assert "Correction status: metadata incomplete" in incomplete.stdout
        assert "Submission contract: missing" in incomplete.stdout
        assert "preflight only" not in incomplete.stdout
        assert "Cannot run strict submission check" not in incomplete.stdout


def test_metadata_incomplete_project_checks_do_not_run_preflight() -> None:
    clean_workspace()
    rendu = ROOT / "workspace" / "rendu"
    rendu.mkdir(parents=True, exist_ok=True)
    (rendu / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    (rendu / "a.out").write_text("artifact\n", encoding="utf-8")
    (rendu / "tests").mkdir()
    (rendu / "tests" / "private.txt").write_text("secret fixture content\n", encoding="utf-8")

    for project_id, label in INCOMPLETE_PROJECTS.items():
        result = run_cli("project", "check", project_id)
        assert result.returncode == 0
        assert "Submission Check" in result.stdout
        assert f"Project        : {label}" in result.stdout
        assert "Status         : metadata incomplete" in result.stdout
        assert "Cannot run strict submission check yet." in result.stdout
        assert "required files" not in result.stdout
        assert "forbidden files" not in result.stdout
        assert "Nothing turned in" not in result.stdout
        assert "secret fixture content" not in result.stdout


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
    incomplete = run_cli("project", "check", "sastantua")
    assert incomplete.returncode == 0
    assert "metadata incomplete" in incomplete.stdout
    assert "Cannot run strict submission check yet." in incomplete.stdout

    rendu = ROOT / "workspace" / "rendu"
    rendu.mkdir(parents=True, exist_ok=True)
    (rendu / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    (rendu / "rush.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    (rendu / "rush-00").write_text("#!/bin/sh\n", encoding="utf-8")
    rush = run_cli("project", "check", "rush00")
    assert "Project        : Rush00" in rush.stdout
    assert "Status         : [OK]" in rush.stdout
    assert "binary         : [OK]" in rush.stdout

    for rush_id, label in [("rush01", "Rush01"), ("rush02", "Rush02")]:
        result = run_cli("project", "check", rush_id)
        assert f"Project        : {label}" in result.stdout
        assert "Status         : [OK]" in result.stdout
        assert "binary" not in result.stdout

    eval_result = run_cli("project", "check", "eval_expr")
    assert "Project        : Eval Expr" in eval_result.stdout
    assert "Status         : [KO]" in eval_result.stdout
    assert "Expected binary `eval_expr` was not found after build." in eval_result.stdout


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

    explicit_rendu = run_cli("project", "check", "bsq", "--source", "rendu")
    assert "Nothing turned in" in explicit_rendu.stdout


def test_project_check_vog_source_fails_without_submitted_snapshot() -> None:
    clean_workspace()

    result = run_cli("project", "check", "bsq", "--source", "vog")

    assert result.returncode == 1
    assert "Vogsphere Source" in result.stdout
    assert "Status         : [KO]" in result.stdout
    assert "Reason         : no submitted snapshot" in result.stdout
    assert 'pforge vog commit -m "message" <name>' in result.stdout
    assert "pforge vog push <name>" in result.stdout
    assert "pforge vog submit <name>" in result.stdout

    assert run_cli("start", "piscine27", "--subject", "p27_pwd_tree").returncode == 0
    moulinette = run_cli("moulinette", "--source", "vog")
    assert moulinette.returncode == 1
    assert "Vogsphere Source" in moulinette.stdout
    assert "Reason         : no submitted snapshot" in moulinette.stdout


def test_project_check_vog_source_uses_submitted_snapshot_without_mutating_rendu() -> None:
    clean_workspace()
    rendu = ROOT / "workspace" / "rendu"
    subject = ROOT / "workspace" / "subject"
    subject.mkdir(parents=True, exist_ok=True)
    (subject / "tests.yml").write_text("hidden subject data\n", encoding="utf-8")
    (subject / "hidden_main.c").write_text("hidden main\n", encoding="utf-8")
    (rendu / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
    (rendu / "bsq").write_text("#!/bin/sh\n", encoding="utf-8")

    run_cli("vog", "init", "bsq")
    commit = run_cli("vog", "commit", "-m", "snapshot", "bsq")
    assert commit.returncode == 0
    run_cli("vog", "push", "bsq")
    run_cli("vog", "submit", "bsq")

    state = json.loads((ROOT / "workspace" / "vogsphere" / "state.json").read_text(encoding="utf-8"))
    commit_id = state["repos"]["bsq"]["submitted"]
    snapshot = ROOT / "workspace" / "vogsphere" / "repos" / "bsq" / "commits" / commit_id
    assert not (snapshot / "tests.yml").exists()
    assert not (snapshot / "hidden_main.c").exists()
    assert not (snapshot / "corrections").exists()

    shutil.rmtree(rendu)
    rendu.mkdir(parents=True, exist_ok=True)

    default_check = run_cli("project", "check", "bsq")
    assert "Nothing turned in" in default_check.stdout

    vog_check = run_cli("project", "check", "bsq", "--source", "vog")

    assert vog_check.returncode == 0
    assert "Project        : BSQ" in vog_check.stdout
    assert "Source         : Vogsphere submitted snapshot" in vog_check.stdout
    assert "Repository     : bsq" in vog_check.stdout
    assert f"Commit         : {commit_id}" in vog_check.stdout
    assert "Status         : [OK]" in vog_check.stdout
    assert not (rendu / "Makefile").exists()
    assert not (rendu / "bsq").exists()
    assert "hidden subject data" not in vog_check.stdout


def test_moulinette_vog_source_uses_snapshot_and_grademe_remains_unchanged() -> None:
    clean_workspace()
    assert run_cli("start", "piscine27", "--subject", "p27_pwd_tree").returncode == 0
    rendu = ROOT / "workspace" / "rendu"
    good = "pwd\nfind . -maxdepth 2 | sort\n"
    (rendu / "p27_pwd_tree.sh").write_text(good, encoding="utf-8")

    run_cli("vog", "init", "p27_pwd_tree")
    run_cli("vog", "commit", "-m", "good solution", "p27_pwd_tree")
    run_cli("vog", "push", "p27_pwd_tree")
    run_cli("vog", "submit", "p27_pwd_tree")
    state = json.loads((ROOT / "workspace" / "vogsphere" / "state.json").read_text(encoding="utf-8"))
    commit_id = state["repos"]["p27_pwd_tree"]["submitted"]

    shutil.rmtree(rendu)
    rendu.mkdir(parents=True, exist_ok=True)

    default_result = run_cli("moulinette", "--source", "rendu")
    assert default_result.returncode == 1
    assert "Source         : workspace/rendu" in default_result.stdout
    assert "submitted files: [KO]" in default_result.stdout

    vog_result = run_cli("moulinette", "--source", "vog")
    assert vog_result.returncode == 0
    assert "Running Moulinette..." in vog_result.stdout
    assert "Source         : Vogsphere submitted snapshot" in vog_result.stdout
    assert "Repository     : p27_pwd_tree" in vog_result.stdout
    assert f"Commit         : {commit_id}" in vog_result.stdout
    assert "Status         : [OK]" in vog_result.stdout
    assert not (rendu / "p27_pwd_tree.sh").exists()

    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--subject", "first_last_char").returncode == 0
    grademe = run_cli("grademe")
    assert "Running Grademe..." in grademe.stdout
    assert "Source         :" not in grademe.stdout


def test_source_help_and_docs_keep_vogsphere_out_of_grademe() -> None:
    forbidden = [
        "Vogsphere source for Grademe",
        "Grademe --source",
        "Grademe may use Vogsphere",
        "Exam may use Vogsphere",
        "optional Vogsphere source for Grademe",
    ]
    for rel in [
        "AGENTS.md",
        "README.md",
        "README_EN.md",
        "README_AR.md",
        "docs/STUDENT_USAGE.md",
        "docs/IMPLEMENTATION_NOTES.md",
    ]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in text
        assert "Vogsphere" in text
        assert "Moulinette" in text
        assert "Grademe" in text

    assert "not supported for Exam yet" not in (ROOT / "piscine_forge" / "cli.py").read_text(encoding="utf-8")

    grademe_help = run_cli("grademe", "--help")
    assert grademe_help.returncode == 0
    assert "--source" not in grademe_help.stdout
    assert "vog" not in grademe_help.stdout

    moulinette_help = run_cli("moulinette", "--help")
    assert moulinette_help.returncode == 0
    assert "--source {rendu,vog}" in moulinette_help.stdout

    project_help = run_cli("project", "check", "--help")
    assert project_help.returncode == 0
    assert "--source {rendu,vog}" in project_help.stdout


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

def test_project_references_reads_static_catalog() -> None:
    assert_no_remote_fetches()

    result = run_cli("project", "references")
    assert result.returncode == 0
    assert "Project References" in result.stdout
    assert "Catalog        : resources/legacy_subjects/references.yml" in result.stdout
    assert "Purpose        : local reference catalog only" in result.stdout
    assert "Remote downloads: disabled" in result.stdout
    assert "ID" in result.stdout
    
    # Check for required legacy projects
    assert "hexanyn_bsq" in result.stdout
    assert "itsanuness_42piscine" in result.stdout
    assert "sebastiencs_piscine_42" in result.stdout
    
    # Check for excluded shell/c modules
    assert "chlimous_42_piscine" not in result.stdout
    assert "shell00" not in result.stdout
    assert "c00" not in result.stdout
    
    # Check for excluded unrelated projects
    assert "red_tetris_candidates" not in result.stdout
    assert "tetris" not in result.stdout

def test_project_references_filtered() -> None:
    result = run_cli("project", "references", "eval_expr")
    assert result.returncode == 0
    assert "Filter         : eval_expr" in result.stdout
    assert "npasquie_evalexpr" in result.stdout
    assert "hexanyn_bsq" not in result.stdout

def test_project_subject_uses_local_files_only() -> None:
    assert_no_remote_fetches()

    result = run_cli("project", "subject", "bsq")
    assert result.returncode == 0
    assert "Project Subject" in result.stdout
    assert "Project        : bsq" in result.stdout
    assert "Reference PDF  : missing" in result.stdout
    assert "Expected local path: resources/legacy_subjects/projects/bsq/subject.pdf" in result.stdout
    assert "Remote downloads: disabled" in result.stdout

def test_project_subject_copy_to(tmp_path) -> None:
    result = run_cli("project", "subject", "bsq", "--copy-to", str(tmp_path))
    assert result.returncode == 1
    assert "Reference PDF  : missing" in result.stdout
    assert "Copy           : failed; local reference PDF is missing" in result.stdout

def test_project_requirements_displays_legacy_metadata() -> None:
    result = run_cli("project", "requirements", "bsq")
    assert result.returncode == 0
    assert "Project Requirements" in result.stdout
    assert "Built-in subject" in result.stdout
    assert "Reference PDF" in result.stdout
    assert "Reference text" in result.stdout
    assert "Local tests" in result.stdout
    assert "Correction status" in result.stdout
    assert "Official 42 services" in result.stdout
    assert "Remote downloads" in result.stdout
    assert "Project Moulinette is a local trainer, not official 42 Moulinette" in result.stdout
