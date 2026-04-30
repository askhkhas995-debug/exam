from __future__ import annotations

import subprocess
from pathlib import Path

from piscine_forge import __version__


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "piscine_forge.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_version_command_and_global_flag() -> None:
    command = run_cli("version")
    assert command.returncode == 0
    assert f"PiscineForge {__version__}" in command.stdout

    flag = run_cli("--version")
    assert flag.returncode == 0
    assert f"PiscineForge {__version__}" in flag.stdout


def test_help_has_product_commands() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "terminal-first 42 Piscine and exam practice" in result.stdout
    assert "doctor" in result.stdout
    assert "version" in result.stdout
    assert "workspace/rendu" in result.stdout


def test_doctor_reports_core_product_state() -> None:
    result = run_cli("doctor")
    assert result.returncode == 0
    assert "PiscineForge Doctor" in result.stdout
    assert "Version" in result.stdout
    assert "Repository" in result.stdout
    assert "Workspace" in result.stdout
    assert "Commands" in result.stdout
    assert "Validation" in result.stdout
    assert "[OK]" in result.stdout


def test_large_curriculum_start_uses_compact_output() -> None:
    result = run_cli("start", "piscine42", "--subject", "ft_print_numbers")
    assert result.returncode == 0
    assert "pool: piscine42_default" in result.stdout
    assert "module: C00 (c00)" in result.stdout
    assert "exercise: ex03" in result.stdout
    assert "subject: ft_print_numbers" in result.stdout
    assert "next: ft_is_negative" in result.stdout
    assert "btree_apply_by_level" not in result.stdout
