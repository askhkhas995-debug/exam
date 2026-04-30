from __future__ import annotations

from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

from piscine_forge.loader import Repository
from piscine_forge.session import Session
from piscine_forge.trace import utc_timestamp


# ---------------------------------------------------------------------------
# Standard failure reason constants
# ---------------------------------------------------------------------------

FAILURE_MISSING_FILE = "missing_file"
FAILURE_EXTRA_FILE = "extra_file"
FAILURE_NORM_ERROR = "norm_error"
FAILURE_FORBIDDEN_FUNCTION = "forbidden_function"
FAILURE_COMPILE_ERROR = "compile_error"
FAILURE_RUNTIME_ERROR = "runtime_error"
FAILURE_TIMEOUT = "timeout"
FAILURE_NOTHING_TURNED_IN = "nothing_turned_in"
FAILURE_SEGMENTATION_FAULT = "segmentation_fault"
FAILURE_BUS_ERROR = "bus_error"
FAILURE_ABORT = "abort"
FAILURE_FLOATING_POINT_EXCEPTION = "floating_point_exception"
FAILURE_WRONG_STDOUT = "wrong_stdout"
FAILURE_WRONG_STDERR = "wrong_stderr"
FAILURE_SHELL_VALIDATOR = "shell_validator_failure"
FAILURE_PROJECT_VALIDATOR = "project_validator_failure"


def base_trace(repo: Repository, session: Session, subject: dict, profile: dict) -> dict:
    meta = subject["meta"]
    state = session.load() if session.state_path.exists() else {}
    return {
        "subject_id": meta["id"],
        "pool_id": state.get("pool_id"),
        "origin": meta.get("origin"),
        "version": meta.get("version"),
        "timestamp": utc_timestamp(),
        "status": "ERROR",
        "failure_reason": "",
        "failure_category": "",
        "checks": [],
        "compile_command": None,
        "test_cases": [],
        "timeout_seconds": int(profile.get("timeout_seconds", 2)),
        "norminette": None,
        "forbidden": None,
    }


def add_check(trace: dict, name: str, status: str, details: str | dict | list | None = None) -> None:
    check = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    trace.setdefault("checks", []).append(check)


def _categorize_failure(reason: str) -> str:
    """Map a failure reason string to a standard category."""
    reason_lower = reason.lower()
    if "missing" in reason_lower and "file" in reason_lower:
        return FAILURE_MISSING_FILE
    if "extra" in reason_lower and "file" in reason_lower:
        return FAILURE_EXTRA_FILE
    if "norm" in reason_lower:
        return FAILURE_NORM_ERROR
    if "forbidden" in reason_lower:
        return FAILURE_FORBIDDEN_FUNCTION
    if "compile" in reason_lower:
        return FAILURE_COMPILE_ERROR
    if "timeout" in reason_lower:
        return FAILURE_TIMEOUT
    if "nothing" in reason_lower and "turned" in reason_lower:
        return FAILURE_NOTHING_TURNED_IN
    if "segmentation" in reason_lower or "sigsegv" in reason_lower:
        return FAILURE_SEGMENTATION_FAULT
    if "bus error" in reason_lower or "sigbus" in reason_lower:
        return FAILURE_BUS_ERROR
    if "sigabrt" in reason_lower or reason_lower == "abort":
        return FAILURE_ABORT
    if "floating point" in reason_lower or "sigfpe" in reason_lower:
        return FAILURE_FLOATING_POINT_EXCEPTION
    if "wrong stdout" in reason_lower or reason == FAILURE_WRONG_STDOUT:
        return FAILURE_WRONG_STDOUT
    if "wrong stderr" in reason_lower or reason == FAILURE_WRONG_STDERR:
        return FAILURE_WRONG_STDERR
    if "shell_validator" in reason_lower:
        return FAILURE_SHELL_VALIDATOR
    if "project_validator" in reason_lower:
        return FAILURE_PROJECT_VALIDATOR
    if "runtime" in reason_lower or "exit code" in reason_lower:
        return FAILURE_RUNTIME_ERROR
    # If the reason is already a standard constant, use it directly
    standard = {
        FAILURE_MISSING_FILE, FAILURE_EXTRA_FILE, FAILURE_NORM_ERROR,
        FAILURE_FORBIDDEN_FUNCTION, FAILURE_COMPILE_ERROR, FAILURE_RUNTIME_ERROR,
        FAILURE_TIMEOUT, FAILURE_NOTHING_TURNED_IN, FAILURE_SEGMENTATION_FAULT,
        FAILURE_BUS_ERROR, FAILURE_ABORT, FAILURE_FLOATING_POINT_EXCEPTION,
        FAILURE_WRONG_STDOUT, FAILURE_WRONG_STDERR,
        FAILURE_SHELL_VALIDATOR, FAILURE_PROJECT_VALIDATOR,
    }
    if reason in standard:
        return reason
    return reason


def fail(trace: dict, reason: str, *, status: str = "KO") -> dict:
    trace["status"] = status
    trace["failure_reason"] = reason
    trace["failure_category"] = _categorize_failure(reason)
    return trace


SIGNAL_FAILURES = {
    signal.SIGSEGV: FAILURE_SEGMENTATION_FAULT,
    signal.SIGBUS: FAILURE_BUS_ERROR,
    signal.SIGABRT: FAILURE_ABORT,
    signal.SIGFPE: FAILURE_FLOATING_POINT_EXCEPTION,
}


def failure_for_returncode(returncode: int | None) -> tuple[str, dict]:
    if returncode is None:
        return FAILURE_RUNTIME_ERROR, {}
    detail: dict = {"returncode": returncode}
    if returncode < 0:
        signum = -returncode
        detail["signal"] = _signal_name(signum)
        category = SIGNAL_FAILURES.get(signal.Signals(signum)) if _valid_signal(signum) else None
        if category:
            return category, detail
    return FAILURE_RUNTIME_ERROR, detail


def fail_runtime(trace: dict, returncode: int | None) -> dict:
    category, detail = failure_for_returncode(returncode)
    if "returncode" in detail:
        trace["returncode"] = detail["returncode"]
    if "signal" in detail:
        trace["signal"] = detail["signal"]
        trace["failure_detail"] = detail["signal"]
    return fail(trace, category)


def fail_empty_submission(trace: dict) -> dict:
    add_check(trace, "submitted_files", "KO", "no visible files submitted")
    return fail(trace, FAILURE_NOTHING_TURNED_IN)


def pass_trace(trace: dict) -> dict:
    trace["status"] = "OK"
    trace["failure_reason"] = ""
    trace["failure_category"] = ""
    return trace


def submission_dir(session: Session, subject_id: str) -> Path:
    nested = session.rendu_dir / subject_id
    if nested.is_dir() and any(nested.iterdir()):
        return nested
    return session.rendu_dir


def visible_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*") if p.is_file() and not any(part.startswith(".") for part in p.relative_to(path).parts))


def has_visible_submission(path: Path) -> bool:
    return bool(visible_files(path))


def _valid_signal(signum: int) -> bool:
    try:
        signal.Signals(signum)
    except ValueError:
        return False
    return True


def _signal_name(signum: int) -> str:
    try:
        return signal.Signals(signum).name
    except ValueError:
        return f"SIG{signum}"


def verify_expected_files(trace: dict, submit: Path, expected: list[str], *, reject_extra: bool) -> tuple[bool, list[Path]]:
    actual = visible_files(submit)
    expected_paths: list[Path] = []
    missing: list[str] = []
    for rel in expected:
        path = submit / rel
        if not path.exists() or not path.is_file():
            missing.append(rel)
        else:
            expected_paths.append(path)
    if missing:
        add_check(trace, "expected_files", "KO", {"missing": missing})
        return False, expected_paths

    expected_set = {str(Path(rel)) for rel in expected}
    extras = [str(path.relative_to(submit)) for path in actual if str(path.relative_to(submit)) not in expected_set]
    if reject_extra and extras:
        add_check(trace, "extra_files", "KO", {"extra": extras})
        return False, expected_paths

    add_check(trace, "expected_files", "OK", {"files": expected})
    if reject_extra:
        add_check(trace, "extra_files", "OK")
    return True, expected_paths


def copy_expected_files(files: list[Path], submit: Path, build: Path) -> list[Path]:
    copied: list[Path] = []
    for file in files:
        rel = file.relative_to(submit)
        target = build / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        copied.append(target)
    return copied


def run_command(
    args: list[str],
    *,
    cwd: Path,
    timeout: int,
    stdin: str | None = None,
) -> tuple[subprocess.CompletedProcess[str] | None, bool]:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc, False
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(args, 124, exc.stdout or "", exc.stderr or "")
        return completed, True


class BuildDir:
    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory(prefix="pforge-")
        return Path(self._tmp.name)

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tmp.cleanup()
