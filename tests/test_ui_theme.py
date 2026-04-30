from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from piscine_forge.interface import _select_exam_by_group, run_menu
from piscine_forge.loader import Repository
from piscine_forge.theme import color, colors_enabled, resolve_theme, strip_ansi
from piscine_forge.ui import RenderContext, render_menu, render_progress_bar, render_separator


ROOT = Path(__file__).resolve().parents[1]


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


class FakeStream:
    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "-m", "piscine_forge.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_official_theme_is_default() -> None:
    assert resolve_theme(None).name == "official"


def test_theme_resolution_and_graphbox_alias() -> None:
    assert resolve_theme("tokyo-night").name == "tokyo-night"
    assert resolve_theme("gruvbox").name == "gruvbox"
    assert resolve_theme("graphbox").name == "gruvbox"
    assert resolve_theme("missing-theme").name == "official"


def test_plain_no_color_and_no_color_env_disable_colors() -> None:
    assert colors_enabled(FakeStream(True), {"PFORGE_THEME": "plain"}) is False
    assert colors_enabled(FakeStream(True), {"PFORGE_THEME": "official", "NO_COLOR": "1"}) is False


def test_non_tty_disables_colors() -> None:
    assert colors_enabled(FakeStream(False), {"PFORGE_THEME": "official"}) is False
    assert colors_enabled(FakeStream(True), {"PFORGE_THEME": "official"}) is True


def test_strip_ansi_works() -> None:
    rendered = color("OK", "success", "official", enabled=True)
    assert rendered != "OK"
    assert strip_ansi(rendered) == "OK"


def test_progress_bar_renders_ascii() -> None:
    assert render_progress_bar(7, 106, width=20) == "[#-------------------] 7 / 106  7%"
    assert render_progress_bar(3, 9, width=10) == "[###-------] 3 / 9  33%"


def test_menu_output_works_without_colors_and_no_emojis() -> None:
    clean_workspace()
    repo = Repository(ROOT)
    output: list[str] = []
    result = run_menu(repo, input_func=lambda prompt="": "0", output=output.append)
    text = "\n".join(output)
    assert result == 0
    assert "PiscineForge" in text
    assert "PiscineForge ExamShell" not in text
    assert "\x1b[" not in text
    assert "____  _____" in text
    assert "Projects" in text
    assert "Vogsphere" in text
    assert "Tools" in text
    assert "Status / Progress / Time" not in text
    assert not re.search(r"[\U0001F300-\U0001FAFF]", text)


def test_banner_can_be_disabled(monkeypatch) -> None:
    clean_workspace()
    monkeypatch.setenv("PFORGE_BANNER", "off")
    repo = Repository(ROOT)
    output: list[str] = []
    result = run_menu(repo, input_func=lambda prompt="": "0", output=output.append)
    text = "\n".join(output)
    assert result == 0
    assert "PiscineForge" in text
    assert "____  _____" not in text


def test_exams_menu_is_grouped_by_pattern() -> None:
    clean_workspace()
    repo = Repository(ROOT)
    output: list[str] = []
    result = _select_exam_by_group(repo, input_func=lambda prompt="": "0", output=output.append)
    text = "\n".join(output)
    assert result is None
    assert "Exams" in text
    assert "ExamShell-style Practice" in text
    assert "Rank Practice" in text
    assert "Handwritten Practice" in text
    assert "Imported Practice" in text
    assert "Classic ExamShell-style Practice" in text
    assert "Handwritten Practice v5" in text
    assert "Official-like" not in text


def test_render_menu_is_plain_by_default() -> None:
    text = render_menu("Title", [("1", "First"), ("0", "Back")])
    assert "Title" in text
    assert "  1  First" in text
    assert "\x1b[" not in text


def test_ascii_separator_fallback() -> None:
    ctx = RenderContext(resolve_theme("plain"), color_enabled=False, unicode=False)
    assert render_separator("Title", ctx=ctx) == "Title\n-----"


def test_status_output_works_without_colors() -> None:
    start = run_cli("start", "piscine42", "--subject", "ft_print_numbers")
    assert start.returncode == 0
    status = run_cli("status")
    assert status.returncode == 0
    assert "Piscine Progress" in status.stdout
    assert "Overall" in status.stdout
    assert "[" in status.stdout and "]" in status.stdout
    assert "\x1b[" not in status.stdout
