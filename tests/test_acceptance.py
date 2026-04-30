from __future__ import annotations

from pathlib import Path
import json
import subprocess


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


PRINT_NTH = r'''/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   print_nth_char.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: pforge <pforge@student.42.fr>              +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/04/26 00:00:00 by pforge            #+#    #+#             */
/*   Updated: 2026/04/26 00:00:00 by pforge           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>

void	print_nth_char(char *str, int n)
{
	int	i;

	if (n <= 0)
	{
		write(1, "\n", 1);
		return ;
	}
	i = 0;
	while (str[i])
	{
		if (i % n == n - 1)
			write(1, &str[i], 1);
		i++;
	}
	write(1, "\n", 1);
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


def write_rendu(name: str, content: str) -> None:
    path = ROOT / "workspace" / "rendu" / name
    path.write_text(content, encoding="utf-8")


def test_validate_and_list_commands() -> None:
    assert run_cli("validate").returncode == 0
    pools = run_cli("list", "pools")
    assert pools.returncode == 0
    assert "handwritten_v5" in pools.stdout
    subjects = run_cli("list", "subjects")
    assert subjects.returncode == 0
    assert "print_nth_char" in subjects.stdout


def test_seeded_exam_and_current_subject() -> None:
    clean_workspace()
    exam = run_cli("exam", "handwritten_v5", "--seed", "42")
    assert exam.returncode == 0
    assert "Exam Started" in exam.stdout
    assert "Exam           : Handwritten Practice v5" in exam.stdout
    assert "Pool           : handwritten_v5" in exam.stdout
    assert "Seed           : 42" in exam.stdout
    assert "Level          : 0 / 5" in exam.stdout
    assert "Exercise       : first_last_char" in exam.stdout
    assert "Correction     : Grademe" in exam.stdout
    current = run_cli("subject", "current")
    assert current.returncode == 0
    assert "first and the last character" in current.stdout


def test_c_program_and_function_and_shell_grademe() -> None:
    clean_workspace()
    write_rendu("first_last_char.c", FIRST_LAST)
    assert run_cli("grademe", "--subject", "first_last_char").returncode == 0

    clean_workspace()
    write_rendu("print_nth_char.c", PRINT_NTH)
    assert run_cli("grademe", "--subject", "print_nth_char").returncode == 0

    clean_workspace()
    write_rendu("p27_pwd_tree.sh", "pwd\nfind . -maxdepth 2 | sort\n")
    assert run_cli("grademe", "--subject", "p27_pwd_tree").returncode == 0


def test_failure_modes_and_trace_generation() -> None:
    clean_workspace()
    missing = run_cli("grademe", "--subject", "alpha_index_case")
    assert missing.returncode == 1
    assert "nothing_turned_in" in missing.stdout

    write_rendu("alpha_index_case.c", "int main(void)\n{\n\treturn broken\n}\n")
    compile_error = run_cli("grademe", "--subject", "alpha_index_case")
    assert compile_error.returncode == 1
    assert "compile_error" in compile_error.stdout

    write_rendu("alpha_index_case.c", '#include <unistd.h>\nint main(void)\n{\n\twrite(1, "wrong\\n", 6);\n\treturn (0);\n}\n')
    wrong = run_cli("grademe", "--subject", "alpha_index_case")
    assert wrong.returncode == 1
    assert "wrong_stdout" in wrong.stdout

    write_rendu("alpha_index_case.c", '#include <stdio.h>\nint main(void)\n{\n\tprintf("Ab Cd!\\n");\n\treturn (0);\n}\n')
    forbidden = run_cli("grademe", "--subject", "alpha_index_case")
    assert forbidden.returncode == 1
    assert "forbidden_function" in forbidden.stdout

    trace = json.loads((ROOT / "workspace" / "traces" / "trace.json").read_text(encoding="utf-8"))
    assert trace["status"] == "KO"
    assert trace["failure_reason"] == "forbidden_function"
    assert (ROOT / "workspace" / "traces" / "traceback.txt").exists()
