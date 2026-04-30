from __future__ import annotations

import os
import shutil

from piscine_forge.compare import exact
from piscine_forge.loader import Repository
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
from .shell_validators import run_validators


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

    script = files[0]

    if profile.get("require_executable", False) and not os.access(script, os.X_OK):
        add_check(trace, "executable_permission", "KO", str(script))
        return fail(trace, "shell_validator_failure: script is not executable")
    add_check(trace, "executable_permission", "OK" if os.access(script, os.X_OK) else "SKIP")

    # Run shell-specific validators if defined in tests.yml
    tests_data = repo.tests_for_subject(subject)
    validator_checks = tests_data.get("validators", [])
    if validator_checks:
        v_ok, v_reason = run_validators(trace, validator_checks, submit, repo.root)
        if not v_ok:
            return fail(trace, v_reason)

    # If this is a non-script exercise (e.g., tar archive, file content),
    # and there are no fixed_tests, the validators above are sufficient.
    fixed_tests = tests_data.get("fixed_tests", [])
    validator_only = meta.get("validator_only", False)
    if validator_only and not fixed_tests:
        return pass_trace(trace)

    # Shell syntax check (only for actual shell scripts)
    if script.suffix in (".sh", "") and not validator_only:
        syntax, timed_out = run_command(["/bin/sh", "-n", str(script)], cwd=submit, timeout=timeout)
        if timed_out or syntax is None or syntax.returncode != 0:
            add_check(trace, "shell_syntax", "KO", syntax.stderr if syntax else "timeout")
            return fail(trace, "shell_validator_failure: syntax error")
        add_check(trace, "shell_syntax", "OK")

    tests = fixed_tests or [{"args": [], "stdout": None}]
    with BuildDir() as build:
        copied = copy_expected_files(files, submit, build)
        copied_script = copied[0]
        for index, test in enumerate(tests, start=1):
            args = [str(arg) for arg in test.get("args", [])]
            fixture_dir = build / f"case_{index}"
            fixture_dir.mkdir()
            for rel, content in (test.get("files") or {}).items():
                target = fixture_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(content), encoding="utf-8")
            run_script = fixture_dir / copied_script.name
            shutil.copy2(copied_script, run_script)
            command = ["/bin/sh", str(run_script), *args]
            proc, timed_out = run_command(command, cwd=fixture_dir, timeout=timeout, stdin=test.get("stdin"))
            actual_stdout = proc.stdout if proc else ""
            actual_stderr = proc.stderr if proc else ""
            expected_stdout = test.get("stdout")
            case = {
                "name": test.get("name", f"fixed_{index}"),
                "command": " ".join(["/bin/sh", copied_script.name, *args]),
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
            contains = test.get("stdout_contains") or []
            if contains:
                missing = [needle for needle in contains if str(needle) not in actual_stdout]
                case["stdout_contains"] = contains
                trace["test_cases"].append(case)
                add_check(trace, f"test_{index}", "OK" if not missing else "KO", {"missing": missing} if missing else None)
                if missing:
                    return fail(trace, "wrong_stdout")
            elif expected_stdout is not None:
                comparison = exact(str(expected_stdout), actual_stdout)
                case["diff"] = comparison.diff
                trace["test_cases"].append(case)
                add_check(trace, f"test_{index}", "OK" if comparison.ok else "KO", comparison.diff or None)
                if not comparison.ok:
                    return fail(trace, "wrong_stdout")
            else:
                trace["test_cases"].append(case)
                add_check(trace, f"test_{index}", "OK", "no stdout expectation")
    return pass_trace(trace)
