from __future__ import annotations

from dataclasses import dataclass
import difflib


@dataclass(frozen=True)
class Comparison:
    ok: bool
    expected: str
    actual: str
    diff: str


def exact(expected: str, actual: str, *, fromfile: str = "expected", tofile: str = "actual") -> Comparison:
    if expected == actual:
        return Comparison(True, expected, actual, "")
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )
    return Comparison(False, expected, actual, diff)


def exact_compare(expected: str, actual: str) -> tuple[bool, str]:
    result = exact(expected, actual)
    return result.ok, result.diff
