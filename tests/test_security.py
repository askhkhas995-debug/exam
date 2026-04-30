"""Tests ensuring correction files are never exposed to the student workspace."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

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
    for sub in ["rendu", "subject", "traces"]:
        path = ROOT / "workspace" / sub
        path.mkdir(parents=True, exist_ok=True)
        for item in path.iterdir():
            if item.name == ".gitkeep":
                continue
            if item.is_dir():
                subprocess.run(["rm", "-rf", str(item)], check=True)
            else:
                item.unlink()


def workspace_files() -> list[Path]:
    """List all files in workspace/subject/."""
    subject_dir = ROOT / "workspace" / "subject"
    if not subject_dir.exists():
        return []
    return list(subject_dir.rglob("*"))


class TestSecurityNoCorrectionsExposed:
    def test_no_correction_in_subject_dir(self):
        """After starting a session, no correction profile should be in workspace/subject."""
        clean_workspace()
        result = run_cli("exam", "handwritten_v5", "--seed", "42")
        assert result.returncode == 0

        files = workspace_files()
        for f in files:
            if f.is_file():
                content = f.read_text(encoding="utf-8", errors="replace")
                # Should not contain correction profile paths
                assert "corrections/" not in content or f.name == "meta.yml"

    def test_meta_yml_strips_correction_path(self):
        """workspace/subject/meta.yml should not expose correction profile path."""
        clean_workspace()
        run_cli("exam", "handwritten_v5", "--seed", "42")

        meta = ROOT / "workspace" / "subject" / "meta.yml"
        if meta.exists():
            content = meta.read_text(encoding="utf-8")
            assert "profile:" not in content or "corrections/" not in content

    def test_no_correction_files_in_rendu(self):
        """workspace/rendu should never contain correction files."""
        clean_workspace()
        run_cli("exam", "handwritten_v5", "--seed", "42")

        rendu = ROOT / "workspace" / "rendu"
        for f in rendu.rglob("*"):
            assert "profile.yml" not in f.name
            assert "hidden_main" not in f.name
