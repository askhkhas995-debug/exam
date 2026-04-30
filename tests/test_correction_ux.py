from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from piscine_forge.interface import run_menu
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


def menu_text() -> str:
    repo = Repository(ROOT)
    output: list[str] = []
    result = run_menu(repo, input_func=lambda prompt="": "0", output=output.append)
    assert result == 0
    return "\n".join(output)


def write_rendu(name: str, content: str) -> None:
    path = ROOT / "workspace" / "rendu" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_menu_correction_label_is_context_aware() -> None:
    clean_workspace()
    inactive_menu = menu_text()
    assert "PiscineForge ExamShell" not in inactive_menu
    assert "Mode          : none" in inactive_menu
    assert "  4  Vogsphere" in inactive_menu
    assert "  5  Tools" in inactive_menu

    assert run_cli("start", "piscine42", "--subject", "ft_print_numbers").returncode == 0
    piscine_menu = menu_text()
    assert "  2  Run Moulinette" in piscine_menu
    assert "Subject       : ft_print_numbers" in piscine_menu
    assert "Grademe" not in piscine_menu
    assert "PiscineForge ExamShell" not in piscine_menu

    assert run_cli("exam", "handwritten_v5", "--subject", "first_last_char").returncode == 0
    exam_menu = menu_text()
    assert "  2  Run Grademe" in exam_menu
    assert "Mode          : Exam" in exam_menu
    assert "Exercise      : first_last_char" in exam_menu
    assert "Moulinette" not in exam_menu


def test_correct_runs_moulinette_in_piscine_mode() -> None:
    clean_workspace()
    assert run_cli("start", "piscine27", "--subject", "p27_pwd_tree").returncode == 0
    write_rendu("p27_pwd_tree.sh", "pwd\nfind . -maxdepth 2 | sort\n")

    result = run_cli("correct")

    assert result.returncode == 0
    assert "Running Moulinette..." in result.stdout
    assert "Moulinette" in result.stdout
    assert "Grademe" not in result.stdout


def test_correct_runs_grademe_in_exam_mode() -> None:
    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--subject", "first_last_char").returncode == 0
    write_rendu("first_last_char.c", FIRST_LAST)

    result = run_cli("correct")

    assert result.returncode == 0
    assert "Running Grademe..." in result.stdout
    assert "Grademe" in result.stdout
    assert "Level unlocked:" in result.stdout or "Exam complete." in result.stdout


def test_status_uses_last_moulinette_or_grademe() -> None:
    clean_workspace()
    assert run_cli("start", "piscine42", "--subject", "ft_print_numbers").returncode == 0
    assert run_cli("correct").returncode == 1
    piscine_current = run_cli("current")
    assert "Correction     : Moulinette" in piscine_current.stdout
    assert "Last Moulinette:" in piscine_current.stdout
    piscine_status = run_cli("status")
    assert piscine_status.returncode == 0
    assert "Last Moulinette" in piscine_status.stdout

    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--subject", "first_last_char").returncode == 0
    assert run_cli("correct").returncode == 1
    exam_current = run_cli("current")
    assert "Mode           : Exam" in exam_current.stdout
    assert "Correction     : Grademe" in exam_current.stdout
    assert "Exercise       : first_last_char" in exam_current.stdout
    assert "Last Grademe   :" in exam_current.stdout
    exam_status = run_cli("status")
    assert exam_status.returncode == 0
    assert "Last Grademe" in exam_status.stdout


def test_grademe_compatibility_uses_active_session_language() -> None:
    clean_workspace()
    assert run_cli("start", "piscine42", "--subject", "ft_print_numbers").returncode == 0

    result = run_cli("grademe")

    assert result.returncode == 1
    assert "Active Piscine sessions use Moulinette" in result.stdout
    assert "Running Moulinette..." in result.stdout
    assert "Moulinette" in result.stdout


def test_moulinette_refuses_exam_session_with_grademe_hint() -> None:
    clean_workspace()
    assert run_cli("exam", "handwritten_v5", "--subject", "first_last_char").returncode == 0

    result = run_cli("moulinette")

    assert result.returncode == 1
    assert "Exam sessions use Grademe" in result.stdout
    assert "pforge grademe" in result.stdout


def test_grademe_subject_without_session_is_manual_correction() -> None:
    clean_workspace()

    result = run_cli("grademe", "--subject", "first_last_char")

    assert result.returncode == 1
    assert "Running manual correction..." in result.stdout
    assert "Correction" in result.stdout
    assert "Running Correction..." not in result.stdout


def test_correct_without_session_asks_for_a_session() -> None:
    clean_workspace()
    result = run_cli("correct")
    assert result.returncode == 1
    assert "No active session." in result.stdout
    assert "pforge start piscine42" in result.stdout
    assert "pforge exam <pool>" in result.stdout


def test_student_docs_distinguish_moulinette_and_grademe() -> None:
    for rel in ["README.md", "README_EN.md", "README_AR.md", "docs/STUDENT_USAGE.md"]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "Moulinette" in text
        assert "Grademe" in text
        assert "pforge correct" in text
        assert "pforge moulinette" in text
        assert "pforge moulinette summary" in text
        assert "pforge grademe" in text
