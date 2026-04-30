from __future__ import annotations

from pathlib import Path
import shutil

from piscine_forge.compare import exact
from piscine_forge.forbidden import contains_main, scan_files
from piscine_forge.loader import Repository
from piscine_forge.norminette import check as norm_check
from piscine_forge.session import Session

from .common import (
    BuildDir,
    add_check,
    base_trace,
    copy_expected_files,
    fail_empty_submission,
    fail_runtime,
    fail,
    has_visible_submission,
    pass_trace,
    run_command,
    submission_dir,
    verify_expected_files,
)


def _hidden_main(meta: dict, tests: list[dict]) -> tuple[str, str]:
    prototype = meta.get("prototype", "")
    lines = ["#include <stdio.h>", "#include <unistd.h>", ""]
    if prototype:
        lines.append(prototype.rstrip(";") + ";")
    lines.append("")
    lines.append("int main(void)")
    lines.append("{")
    expected = ""
    for test in tests:
        if "call" in test:
            lines.append(f"    {test['call'].rstrip(';')};")
            expected += str(test.get("stdout", ""))
        elif "expr" in test:
            lines.append(f"    printf(\"%ld\\n\", (long)({test['expr']}));")
            expected += str(test.get("stdout", f"{test.get('return', '')}\n"))
    lines.append("    return (0);")
    lines.append("}")
    return "\n".join(lines) + "\n", expected


def evaluate(repo: Repository, session: Session, subject: dict) -> dict:
    meta = subject["meta"]
    profile = repo.correction_profile(subject)
    trace = base_trace(repo, session, subject, profile)
    submit = submission_dir(session, meta["id"])
    expected = list(meta.get("expected_files", []))
    grading = repo.config("grading").get("grading", {})
    reject_extra = bool(grading.get("reject_extra_files", True))
    timeout = int(profile.get("timeout_seconds", grading.get("timeout_seconds", 2)))

    if not has_visible_submission(submit):
        return fail_empty_submission(trace)

    ok, files = verify_expected_files(trace, submit, expected, reject_extra=reject_extra)
    if not ok:
        return fail(trace, "missing_file")

    if any(contains_main(path) for path in files) and not meta.get("allow_main", False):
        add_check(trace, "main_rejected", "KO", "main is not allowed in function exercises")
        return fail(trace, "forbidden_function")
    add_check(trace, "main_rejected", "OK")

    norm = norm_check(repo.root, files, bool(meta.get("norminette", False)))
    trace["norminette"] = norm.__dict__
    add_check(trace, "norminette", norm.status, norm.reason or norm.stdout or norm.stderr)
    norm_failed = not norm.ok

    forbidden = scan_files(files, meta.get("forbidden_functions", []))
    trace["forbidden"] = {"ok": forbidden.ok, "hits": forbidden.hits}
    add_check(trace, "forbidden_functions", "OK" if forbidden.ok else "KO", forbidden.hits)
    if not forbidden.ok:
        return fail(trace, "forbidden_function")

    if shutil.which("gcc") is None:
        add_check(trace, "compile", "ERROR", "gcc not found")
        return fail(trace, "gcc not found", status="ERROR")

    tests = repo.tests_for_subject(subject).get("fixed_tests", []) or []
    if not tests:
        return fail(trace, "no function tests configured", status="ERROR")


    with BuildDir() as build:
        copied = copy_expected_files(files, submit, build)
        hidden_source, expected_stdout = _hidden_main(meta, tests)
        hidden = build / "__hidden_main.c"
        hidden.write_text(hidden_source, encoding="utf-8")
        binary = build / "__pforge_func_bin"
        flags = grading.get("compile_flags", ["-Wall", "-Wextra", "-Werror"])
        cmd = ["gcc", *flags, *[str(path.relative_to(build)) for path in copied], hidden.name, "-o", str(binary)]
        trace["compile_command"] = " ".join(cmd)
        proc, timed_out = run_command(cmd, cwd=build, timeout=timeout)
        if timed_out or proc is None or proc.returncode != 0:
            add_check(trace, "compile", "KO", (proc.stderr if proc else "timeout").strip())
            return fail(trace, "compile_error" if not timed_out else "timeout")
        add_check(trace, "compile", "OK")

        proc, timed_out = run_command([str(binary)], cwd=build, timeout=timeout)
        actual_stdout = proc.stdout if proc else ""
        actual_stderr = proc.stderr if proc else ""
        case = {
            "name": "hidden_main",
            "command": f"./{binary.name}",
            "expected_stdout": expected_stdout,
            "actual_stdout": actual_stdout,
            "stderr": actual_stderr,
            "returncode": proc.returncode if proc else None,
            "timeout": timed_out,
        }
        if timed_out:
            trace["test_cases"].append(case)
            add_check(trace, "hidden_main", "KO", "timeout")
            return fail(trace, "timeout")
        if proc and proc.returncode != 0:
            trace["test_cases"].append(case)
            add_check(trace, "hidden_main", "KO", f"exit code {proc.returncode}")
            return fail_runtime(trace, proc.returncode)

        comparison = exact(expected_stdout, actual_stdout)
        case["diff"] = comparison.diff
        trace["test_cases"].append(case)
        add_check(trace, "hidden_main", "OK" if comparison.ok else "KO", comparison.diff or None)
        if not comparison.ok:
            return fail(trace, "wrong_stdout")
    if norm_failed:
        return fail(trace, "norm_error")
    return pass_trace(trace)
