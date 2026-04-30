from __future__ import annotations


MOULINETTE_LABELS = {
    "compile_error": "Does not compile",
    "nothing_turned_in": "Nothing turned in",
    "timeout": "Timeout",
    "segmentation_fault": "Segmentation fault",
    "bus_error": "Bus error",
    "abort": "Abort",
    "floating_point_exception": "Floating point exception",
}


HUMAN_REASONS = {
    "wrong_stdout": "stdout mismatch",
    "wrong_stderr": "stderr mismatch",
    "missing_file": "missing file",
    "extra_file": "extra file",
    "compile_error": "Does not compile",
    "runtime_error": "runtime error",
    "forbidden_function": "forbidden function",
    "norm_error": "norm error",
    "timeout": "Timeout",
    "nothing_turned_in": "Nothing turned in",
    "segmentation_fault": "Segmentation fault",
    "bus_error": "Bus error",
    "abort": "Abort",
    "floating_point_exception": "Floating point exception",
}


def failure_category(result: dict | None) -> str:
    result = result or {}
    return str(result.get("failure_category") or result.get("category") or result.get("reason") or result.get("failure_reason") or "")


def human_reason_for(result: dict | None) -> str:
    result = result or {}
    reason = str(result.get("reason") or result.get("failure_reason") or "")
    category = failure_category(result) or reason
    return HUMAN_REASONS.get(category, reason)


def moulinette_label_for(result: dict | None) -> str:
    result = result or {}
    status = str(result.get("status") or "").upper()
    if status == "OK":
        return "[OK]"
    category = failure_category(result)
    if category in MOULINETTE_LABELS:
        return MOULINETTE_LABELS[category]
    return "[KO]"
