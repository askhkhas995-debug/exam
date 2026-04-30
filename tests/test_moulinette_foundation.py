from __future__ import annotations

from pathlib import Path
import json
import shutil
import signal
import subprocess

from piscine_forge.evaluators.common import failure_for_returncode
from piscine_forge.failure_labels import moulinette_label_for
from piscine_forge.interface import _exam_group, _select_exam_by_group
from piscine_forge.loader import Repository


ROOT = Path(__file__).resolve().parents[1]
DIFF_FIXTURE = ROOT / "resources" / "piscine" / "shell00" / "diff" / "sw.diff"


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


def write_rendu(name: str, content: str) -> None:
    path = ROOT / "workspace" / "rendu" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def start_diff() -> None:
    result = run_cli("start", "piscine42", "--subject", "diff")
    assert result.returncode == 0


def latest_trace() -> dict:
    return json.loads((ROOT / "workspace" / "traces" / "latest.json").read_text(encoding="utf-8"))


def test_moulinette_signal_labels_are_centralized() -> None:
    assert moulinette_label_for({"status": "OK"}) == "[OK]"
    assert moulinette_label_for({"status": "KO", "failure_category": "compile_error"}) == "Does not compile"
    assert moulinette_label_for({"status": "KO", "failure_category": "wrong_stdout"}) == "[KO]"
    assert failure_for_returncode(-signal.SIGSEGV)[0] == "segmentation_fault"
    assert failure_for_returncode(-signal.SIGBUS)[0] == "bus_error"
    assert failure_for_returncode(-signal.SIGABRT)[0] == "abort"
    assert failure_for_returncode(-signal.SIGFPE)[0] == "floating_point_exception"


def test_shell00_diff_correct_submission_passes() -> None:
    clean_workspace()
    start_diff()
    write_rendu("diff", DIFF_FIXTURE.read_text(encoding="utf-8"))
    result = run_cli("moulinette")
    assert result.returncode == 0
    assert "Status         : [OK]" in result.stdout
    assert latest_trace()["status"] == "OK"


def test_shell00_diff_wrong_submission_fails() -> None:
    clean_workspace()
    start_diff()
    write_rendu("diff", "wrong\n")
    result = run_cli("moulinette")
    assert result.returncode == 1
    assert "content mismatch" in result.stdout
    trace = latest_trace()
    assert trace["status"] == "KO"
    assert trace["failure_category"] == "shell_validator_failure"


def test_shell00_diff_missing_and_empty_submission_are_distinct() -> None:
    clean_workspace()
    start_diff()
    empty = run_cli("moulinette")
    assert empty.returncode == 1
    assert "Nothing turned in" in empty.stdout
    assert latest_trace()["failure_category"] == "nothing_turned_in"

    clean_workspace()
    start_diff()
    write_rendu("not_diff", "some content\n")
    missing = run_cli("moulinette")
    assert missing.returncode == 1
    assert "missing file" in missing.stdout
    assert "Nothing turned in" not in missing.stdout
    assert latest_trace()["failure_category"] == "missing_file"


def test_shell00_diff_private_fixture_is_not_copied_to_workspace_subject() -> None:
    clean_workspace()
    start_diff()
    subject_names = {path.name for path in (ROOT / "workspace" / "subject").iterdir()}
    assert "sw.diff" not in subject_names
    assert "._a" not in subject_names
    assert "._sw.diff" not in subject_names
    resource_names = {path.name for path in (ROOT / "resources" / "piscine" / "shell00" / "diff").iterdir()}
    assert resource_names == {"a", "sw.diff"}


def test_moulinette_summary_is_separate_from_single_exercise_flow() -> None:
    clean_workspace()
    result = run_cli("start", "piscine42", "--subject", "ft_print_numbers")
    assert result.returncode == 0
    summary = run_cli("moulinette", "summary")
    assert summary.returncode == 0
    assert "Moulinette Summary" in summary.stdout
    assert "Grade" not in summary.stdout
    assert "Score          : not configured" in summary.stdout
    assert "ft_print_numbers" in summary.stdout
    assert "Pending" in summary.stdout
    assert "ft_print_alphabet" in summary.stdout


def test_moulinette_help_documents_summary_without_internal_arg_name() -> None:
    result = run_cli("moulinette", "--help")
    assert result.returncode == 0
    assert "pforge moulinette summary" in result.stdout
    assert "{summary|SUBJECT}" in result.stdout
    assert "subject_arg" not in result.stdout


def test_exam_metadata_loads_and_menu_prefers_display_names() -> None:
    repo = Repository(ROOT)
    classic = repo.get_pool("classic_v1")
    handwritten = repo.get_pool("handwritten_v5")
    assert classic["display_name"] == "Classic ExamShell-style Practice"
    assert classic["group"] == "ExamShell-style Practice"
    assert classic["official_like"] is False
    assert handwritten["display_name"] == "Handwritten Practice v5"
    assert _exam_group("whatever", {"group": "Custom group"}) == "Custom group"
    assert _exam_group("rank_fallback", {"origin": "rank legacy"}) == "Rank Practice"

    clean_workspace()
    output: list[str] = []
    result = _select_exam_by_group(repo, input_func=lambda prompt="": "0", output=output.append)
    text = "\n".join(output)
    assert result is None
    assert "Classic ExamShell-style Practice (classic_v1)" in text
    assert "Handwritten Practice v5 (handwritten_v5)" in text
    assert "Legacy 1337 Practice 2025 (1337_2025_v4)" in text
    assert "Official-like" not in text


def test_version_file_and_license_are_share_readiness_explicit() -> None:
    assert "Version: 0.1.0" in (ROOT / "VERSION.txt").read_text(encoding="utf-8")
    assert "0.5" not in (ROOT / "VERSION.txt").read_text(encoding="utf-8")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "License not selected yet." in license_text
    assert "not an open-source license" in license_text
