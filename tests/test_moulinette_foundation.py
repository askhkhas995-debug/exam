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
BSQ_RUNNER = """#!/usr/bin/env python3
import sys
from pathlib import Path

ERROR_EXIT = __ERROR_EXIT__


def map_error():
    sys.stderr.write("map error\\n")
    raise SystemExit(ERROR_EXIT)


def solve(raw):
    if raw == "":
        map_error()
    lines = raw.splitlines()
    if not lines:
        map_error()
    header = lines[0]
    if len(header) < 4 or not header[:-3].isdigit():
        map_error()
    expected_rows = int(header[:-3])
    empty = header[-3]
    obstacle = header[-2]
    fill = header[-1]
    if expected_rows <= 0 or len({empty, obstacle, fill}) != 3:
        map_error()
    rows = lines[1:]
    if len(rows) != expected_rows or not rows or not rows[0]:
        map_error()
    width = len(rows[0])
    grid = []
    for row in rows:
        if len(row) != width:
            map_error()
        if any(ch not in (empty, obstacle) for ch in row):
            map_error()
        grid.append(list(row))

    dp = [[0] * width for _ in grid]
    max_size = 0
    max_r = 0
    max_c = 0
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == empty:
                if r == 0 or c == 0:
                    dp[r][c] = 1
                else:
                    dp[r][c] = min(dp[r - 1][c], dp[r][c - 1], dp[r - 1][c - 1]) + 1
                if dp[r][c] > max_size:
                    max_size = dp[r][c]
                    max_r = r
                    max_c = c
    for r in range(max_r - max_size + 1, max_r + 1):
        for c in range(max_c - max_size + 1, max_c + 1):
            grid[r][c] = fill
    return "\\n".join("".join(row) for row in grid) + "\\n"


def main():
    if len(sys.argv) < 2:
        map_error()
    sys.stdout.write("".join(solve(Path(arg).read_text(encoding="utf-8")) for arg in sys.argv[1:]))


if __name__ == "__main__":
    main()
"""


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


def write_bsq_runner(error_exit_code: int = 1) -> None:
    write_rendu("Makefile", "all:\n\tcp bsq.py bsq\n\tchmod +x bsq\n")
    write_rendu("bsq.py", BSQ_RUNNER.replace("__ERROR_EXIT__", str(error_exit_code)))


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


def test_bsq_project_moulinette_validates_stdout_stderr_and_exit_code() -> None:
    clean_workspace()
    assert run_cli("start", "piscine42", "--subject", "bsq").returncode == 0
    write_bsq_runner(error_exit_code=1)

    result = run_cli("moulinette")

    assert result.returncode == 0
    trace = latest_trace()
    assert trace["status"] == "OK"
    invalid_cases = [case for case in trace["test_cases"] if case["name"].startswith("invalid_")]
    assert invalid_cases
    assert all(case["expected_stderr"] == "map error\n" for case in invalid_cases)
    assert all(case["expected_exit_code"] == 1 for case in invalid_cases)


def test_bsq_invalid_map_reports_error_when_exit_code_is_wrong() -> None:
    clean_workspace()
    assert run_cli("start", "piscine42", "--subject", "bsq").returncode == 0
    write_bsq_runner(error_exit_code=0)

    result = run_cli("moulinette")

    assert result.returncode == 1
    trace = latest_trace()
    assert trace["status"] == "KO"
    assert trace["failure_category"] == "project_validator_failure"
    failed = trace["checks"][-1]
    assert failed["status"] == "KO"
    assert "expected exit code 1" in failed["details"]


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
