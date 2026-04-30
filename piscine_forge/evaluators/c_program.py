from __future__ import annotations

from pathlib import Path
import shutil

from piscine_forge.compare import exact
from piscine_forge.forbidden import scan_files
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
    with BuildDir() as build:
        copied = copy_expected_files(files, submit, build)
        binary = build / "__pforge_bin"
        flags = grading.get("compile_flags", ["-Wall", "-Wextra", "-Werror"])
        cmd = ["gcc", *flags, *[str(path.relative_to(build)) for path in copied], "-o", str(binary)]
        trace["compile_command"] = " ".join(cmd)
        proc, timed_out = run_command(cmd, cwd=build, timeout=timeout)
        if timed_out or proc is None or proc.returncode != 0:
            add_check(trace, "compile", "KO", (proc.stderr if proc else "timeout").strip())
            return fail(trace, "compile_error" if not timed_out else "timeout")
        add_check(trace, "compile", "OK")

        for index, test in enumerate(tests or [{"args": [], "stdout": None}], start=1):
            args = [str(arg) for arg in test.get("args", [])]
            command = [str(binary), *args]
            proc, timed_out = run_command(command, cwd=build, timeout=timeout, stdin=test.get("stdin"))
            actual_stdout = proc.stdout if proc else ""
            actual_stderr = proc.stderr if proc else ""
            expected_stdout = test.get("stdout")
            case = {
                "name": test.get("name", f"fixed_{index}"),
                "command": " ".join([f"./{binary.name}", *args]),
                "expected_stdout": expected_stdout,
                "actual_stdout": actual_stdout,
                "stderr": actual_stderr,
                "returncode": proc.returncode if proc else None,
                "timeout": timed_out,
            }
            if timed_out:
                trace["test_cases"].append(case)
                add_check(trace, f"test_{index}", "KO", "timeout")
                return fail(trace, "timeout")

            if proc and proc.returncode != int(test.get("exit_code", 0)):
                trace["test_cases"].append(case)
                add_check(trace, f"test_{index}", "KO", f"exit code {proc.returncode}")
                return fail_runtime(trace, proc.returncode)
            if expected_stdout is not None:
                comparison = exact(str(expected_stdout), actual_stdout)
                case["diff"] = comparison.diff
                trace["test_cases"].append(case)
                add_check(trace, f"test_{index}", "OK" if comparison.ok else "KO", comparison.diff or None)
                if not comparison.ok:
                    return fail(trace, "wrong_stdout")
            else:
                trace["test_cases"].append(case)
                add_check(trace, f"test_{index}", "OK", "no stdout expectation")
    if norm_failed:
        return fail(trace, "norm_error")
    return pass_trace(trace)
