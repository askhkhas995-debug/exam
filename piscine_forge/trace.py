from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_trace(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("timestamp", utc_timestamp())
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_trace(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_trace_stamp(trace: dict) -> str:
    timestamp = str(trace.get("timestamp") or utc_timestamp())
    stamp = timestamp.replace(":", "").replace("-", "").replace("+0000", "Z")
    stamp = stamp.replace(".", "").replace("Z", "Z")
    return re.sub(r"[^0-9TZ]", "", stamp) or "trace"


def _safe_subject_id(trace: dict) -> str:
    subject_id = str(trace.get("subject_id") or "subject")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", subject_id)


def trace_path(trace_dir: Path, trace: dict) -> Path:
    return trace_dir / f"{_safe_trace_stamp(trace)}-{_safe_subject_id(trace)}.json"


def latest_trace(trace_dir: Path) -> Path | None:
    if not trace_dir.exists():
        return None
    for name in ["latest.json", "trace.json"]:
        path = trace_dir / name
        if path.exists():
            return path
    traces = sorted(trace_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)
    return traces[-1] if traces else None


def summarize_trace(data: dict) -> str:
    status = data.get("status", "ERROR")
    reason = data.get("failure_reason") or data.get("failure_category") or ""
    lines = [
        f"Subject: {data.get('subject_id', 'unknown')}",
        f"Status: {status}",
    ]
    if reason:
        lines.append(f"Reason: {reason}")
    checks = data.get("checks") or []
    if checks:
        lines.append("")
        lines.append("Checks:")
        for check in checks:
            detail = check.get("details")
            suffix = f" - {detail}" if detail else ""
            lines.append(f"[{check.get('status', '?')}] {check.get('name', 'check')}{suffix}")
    return "\n".join(lines)


FAILURE_LABELS = {
    "missing_file": "MISSING FILE",
    "extra_file": "EXTRA FILE",
    "norm_error": "NORMINETTE ERROR",
    "forbidden_function": "FORBIDDEN FUNCTION",
    "compile_error": "COMPILE ERROR",
    "runtime_error": "RUNTIME ERROR",
    "timeout": "TIMEOUT",
    "nothing_turned_in": "NOTHING TURNED IN",
    "segmentation_fault": "SEGMENTATION FAULT",
    "bus_error": "BUS ERROR",
    "abort": "ABORT",
    "floating_point_exception": "FLOATING POINT EXCEPTION",
    "wrong_stdout": "WRONG STDOUT",
    "wrong_stderr": "WRONG STDERR",
    "shell_validator_failure": "SHELL VALIDATOR FAILURE",
    "project_validator_failure": "PROJECT VALIDATOR FAILURE",
}


def traceback_text(trace: dict) -> str:
    lines: list[str] = []
    lines.append(f"PiscineForge trace for {trace.get('subject_id', 'unknown')}")
    lines.append(f"status: {trace.get('status', 'ERROR')}")

    failure = trace.get("failure_reason", "")
    category = trace.get("failure_category", "")
    if failure:
        label = FAILURE_LABELS.get(category, category.upper() if category else "FAILURE")
        lines.append(f"failure: [{label}] {failure}")
    lines.append("")

    # Checks summary
    checks = trace.get("checks", [])
    if checks:
        lines.append("--- checks ---")
        for check in checks:
            status = check.get("status", "?")
            name = check.get("name", "check")
            lines.append(f"[{status}] {name}")
            details = check.get("details")
            if details:
                if isinstance(details, dict):
                    for k, v in details.items():
                        lines.append(f"      {k}: {v}")
                elif isinstance(details, list):
                    for item in details:
                        lines.append(f"      - {item}")
                else:
                    lines.append(f"      {details}")
        lines.append("")

    # Norminette
    norm = trace.get("norminette")
    if norm and isinstance(norm, dict):
        lines.append(f"--- norminette: {norm.get('status', 'N/A')} ---")
        if norm.get("reason"):
            lines.append(f"  reason: {norm['reason']}")
        if norm.get("stdout"):
            lines.append(norm["stdout"].rstrip())
        lines.append("")

    # Forbidden functions
    forbidden = trace.get("forbidden")
    if forbidden and isinstance(forbidden, dict) and not forbidden.get("ok", True):
        lines.append("--- forbidden functions ---")
        for name, files in forbidden.get("hits", {}).items():
            for f in files:
                lines.append(f"  {f}: {name}()")
        lines.append("")

    # Compile command
    if trace.get("compile_command"):
        lines.append(f"compile: {trace['compile_command']}")
        lines.append("")

    # Test cases
    for idx, case in enumerate(trace.get("test_cases", []), start=1):
        lines.append(f"----------------8<-------------[ START TEST {idx}: {case.get('name', '')} ]")
        lines.append(f"command: {case.get('command', '')}")
        if case.get("timeout"):
            lines.append("TIMEOUT: execution exceeded time limit")
        if "expected_stdout" in case:
            lines.append("expected stdout:")
            lines.append("" if case.get("expected_stdout") is None else str(case.get("expected_stdout", "")))
        if "actual_stdout" in case:
            lines.append("actual stdout:")
            lines.append(str(case.get("actual_stdout", "")))
        if case.get("diff"):
            lines.append("diff:")
            lines.append(case["diff"])
        if case.get("stderr"):
            lines.append("stderr:")
            lines.append(case["stderr"])
        if case.get("returncode") is not None:
            lines.append(f"exit code: {case['returncode']}")
        lines.append("----------------8<------------- END TEST ]")
    return "\n".join(lines).rstrip() + "\n"


def write_trace_bundle(trace_dir: Path, trace: dict) -> dict[str, Path]:
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace.setdefault("timestamp", utc_timestamp())
    timestamped = trace_path(trace_dir, trace)
    write_trace(timestamped, trace)
    write_trace(trace_dir / "trace.json", trace)
    write_trace(trace_dir / "latest.json", trace)
    (trace_dir / "traceback.txt").write_text(traceback_text(trace), encoding="utf-8")
    return {
        "json": trace_dir / "trace.json",
        "latest": trace_dir / "latest.json",
        "timestamped": timestamped,
        "traceback": trace_dir / "traceback.txt",
    }
