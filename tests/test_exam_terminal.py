from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from piscine_forge.interface import _select_exam_by_group, run_menu
from piscine_forge.loader import Repository


ROOT = Path(__file__).resolve().parents[1]


FIRST_LAST = r'''/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   first_last_char.c                                  :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: pforge <pforge@student.42.fr>              +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/04/26 00:00:00 by pforge            #+#    #+#             */
/*   Updated: 2026/04/26 00:00:00 by pforge           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>

int	main(int argc, char **argv)
{
	char	first;
	int		i;

	if (argc == 2 && argv[1][0])
	{
		first = argv[1][0];
		i = 0;
		while (argv[1][i + 1])
			i++;
		write(1, &first, 1);
		write(1, &argv[1][i], 1);
	}
	write(1, "\n", 1);
	return (0);
}
'''


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
    for sub in ["rendu", "subject", "traces", "vogsphere"]:
        path = workspace / sub
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
    for name in ["session.json", "progress.json"]:
        path = workspace / name
        if path.exists():
            path.unlink()


def write_rendu(name: str, content: str) -> None:
    path = ROOT / "workspace" / "rendu" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_exam_menu_is_metadata_grouped_without_authenticity_claims() -> None:
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
    assert "Legacy Practice" in text
    assert "Classic ExamShell-style Practice (classic_v1)" in text
    assert "Handwritten Practice v5 (handwritten_v5)" in text
    assert "Official-like" not in text
    assert "Official ExamShell" not in text
    assert "not configured" not in text
    assert "4 hours" not in text


def test_exam_start_status_rules_and_current_screen_are_grademe_oriented() -> None:
    clean_workspace()

    started = run_cli("exam", "handwritten_v5", "--seed", "42")
    assert started.returncode == 0
    assert "Exam Started" in started.stdout
    assert "Exam           : Handwritten Practice v5" in started.stdout
    assert "Pool           : handwritten_v5" in started.stdout
    assert "Seed           : 42" in started.stdout
    assert "Level          : 0 / 5" in started.stdout
    assert "Exercise       : first_last_char" in started.stdout
    assert "Correction     : Grademe" in started.stdout
    assert "pforge grademe" in started.stdout

    status = run_cli("exam", "status")
    assert status.returncode == 0
    assert "Exam Status" in status.stdout
    assert "[>]  level 0  first_last_char" in status.stdout
    assert "Timer" in status.stdout
    assert "Duration       : 4 hours" in status.stdout
    assert "Remaining      :" in status.stdout
    assert "Last Grademe" in status.stdout

    rules = run_cli("exam", "rules")
    assert rules.returncode == 0
    assert "Exam Rules" in rules.stdout
    assert "Exam mode uses Grademe, not Moulinette." in rules.stdout

    current = run_cli("exam", "current")
    assert current.returncode == 0
    assert "Exam" in current.stdout
    assert "Instructions" in current.stdout
    assert "Actions" in current.stdout
    assert "  2  Run Grademe" in current.stdout
    assert "Vogsphere" not in current.stdout


def test_active_exam_main_menu_uses_grademe_action() -> None:
    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--seed", "42").returncode == 0

    repo = Repository(ROOT)
    output: list[str] = []
    result = run_menu(repo, input_func=lambda prompt="": "0", output=output.append)
    text = "\n".join(output)

    assert result == 0
    assert "Mode          : Exam" in text
    assert "Exam          : Handwritten Practice v5 (handwritten_v5)" in text
    assert "Exercise      : first_last_char" in text
    assert "Correction    : Grademe" in text
    assert "  2  Run Grademe" in text
    assert "Run Moulinette" not in text


def test_grademe_output_shows_exam_context_and_unlocks_next_level() -> None:
    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--subject", "first_last_char").returncode == 0
    write_rendu("first_last_char.c", FIRST_LAST)

    result = run_cli("grademe")

    assert result.returncode == 0
    assert "Running Grademe..." in result.stdout
    assert "Grademe" in result.stdout
    assert "Exam           : Handwritten Practice v5" in result.stdout
    assert "Level          : 0 / 5" in result.stdout
    assert "Exercise       : first_last_char" in result.stdout
    assert "Status         : [OK]" in result.stdout
    assert "Trace          : workspace/traces/latest.json" in result.stdout
    assert "Next" in result.stdout
    assert "Level unlocked: 1 / 5" in result.stdout


def test_moulinette_refuses_active_exam_session() -> None:
    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--subject", "first_last_char").returncode == 0

    result = run_cli("moulinette")

    assert result.returncode == 1
    assert "Exam sessions use Grademe" in result.stdout
    assert "pforge grademe" in result.stdout
