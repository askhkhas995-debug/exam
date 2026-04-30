from __future__ import annotations

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
    fail_empty_submission,
    fail_runtime,
    fail,
    has_visible_submission,
    pass_trace,
    run_command,
    submission_dir,
    visible_files,
)


def evaluate(repo: Repository, session: Session, subject: dict) -> dict:
    meta = subject["meta"]
    profile = repo.correction_profile(subject)
    trace = base_trace(repo, session, subject, profile)
    submit = submission_dir(session, meta["id"])
    timeout = int(profile.get("timeout_seconds", 10))

    if not has_visible_submission(submit):
        return fail_empty_submission(trace)

    if not (submit / "Makefile").exists():
        add_check(trace, "makefile", "KO", "Makefile missing")
        return fail(trace, "missing_file")
    add_check(trace, "makefile", "OK")

    c_files = [path for path in visible_files(submit) if path.suffix == ".c"]
    norm = norm_check(repo.root, c_files, bool(meta.get("norminette", False)))
    trace["norminette"] = norm.__dict__
    add_check(trace, "norminette", norm.status, norm.reason or norm.stdout or norm.stderr)
    norm_failed = not norm.ok

    forbidden = scan_files(c_files, meta.get("forbidden_functions", []))
    trace["forbidden"] = {"ok": forbidden.ok, "hits": forbidden.hits}
    add_check(trace, "forbidden_functions", "OK" if forbidden.ok else "KO", forbidden.hits)
    if not forbidden.ok:
        return fail(trace, "forbidden_function")

    if shutil.which("make") is None:
        add_check(trace, "make", "ERROR", "make not found")
        return fail(trace, "compile_error", status="ERROR")
    proc, timed_out = run_command(["make"], cwd=submit, timeout=timeout)
    trace["compile_command"] = "make"
    if timed_out or proc is None or proc.returncode != 0:
        add_check(trace, "make", "KO", (proc.stderr if proc else "timeout").strip())
        return fail(trace, "compile_error" if not timed_out else "timeout")
    add_check(trace, "make", "OK", proc.stdout)

    # --- BSQ / project-specific test runner ---
    binary_name = profile.get("binary", meta.get("binary"))
    tests = repo.tests_for_subject(subject).get("fixed_tests", [])
    if binary_name and tests:
        binary = submit / binary_name
        if not binary.exists():
            add_check(trace, "binary", "KO", f"{binary_name} not found after make")
            return fail(trace, "compile_error")
        add_check(trace, "binary", "OK")

        for index, test in enumerate(tests, start=1):
            args = [str(a) for a in test.get("args", [])]
            stdin_text = test.get("stdin")
            test_timeout = int(test.get("timeout", timeout))

            # If the test specifies a map_file, write it to a temp dir and pass it
            with BuildDir() as build:
                if test.get("map_content"):
                    map_file = build / "map.txt"
                    map_file.write_text(str(test["map_content"]), encoding="utf-8")
                    args = [str(map_file) if a == "MAP_FILE" else a for a in args]
                    if not args:
                        args = [str(map_file)]

                command = [str(binary), *args]
                proc, timed_out = run_command(
                    command, cwd=submit, timeout=test_timeout, stdin=stdin_text
                )
                actual_stdout = proc.stdout if proc else ""
                actual_stderr = proc.stderr if proc else ""
                expected_stdout = test.get("stdout")
                case = {
                    "name": test.get("name", f"project_test_{index}"),
                    "command": " ".join([f"./{binary_name}", *args]),
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
                if test.get("expect_error") and proc and proc.returncode == 0:
                    trace["test_cases"].append(case)
                    add_check(trace, f"test_{index}", "KO", "expected error but got success")
                    return fail(trace, "project_validator_failure")
                if not test.get("expect_error") and proc and proc.returncode != int(test.get("exit_code", 0)):
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
                    add_check(trace, f"test_{index}", "OK")

    if norm_failed:
        return fail(trace, "norm_error")
    return pass_trace(trace)
