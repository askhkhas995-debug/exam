from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


@dataclass(frozen=True)
class ForbiddenResult:
    ok: bool
    hits: dict[str, list[str]]


def _strip_comments_and_strings(source: str) -> str:
    source = _COMMENT_RE.sub(" ", source)
    return _STRING_RE.sub(" ", source)


def scan_files(files: list[Path], forbidden: list[str] | None) -> ForbiddenResult:
    names = [name for name in (forbidden or []) if name]
    hits: dict[str, list[str]] = {}
    if not names:
        return ForbiddenResult(True, hits)

    patterns = {name: re.compile(rf"\b{re.escape(name)}\s*\(") for name in names}
    for path in files:
        if not path.exists() or not path.is_file():
            continue
        try:
            stripped = _strip_comments_and_strings(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        for name, pattern in patterns.items():
            if pattern.search(stripped):
                hits.setdefault(name, []).append(str(path))
    return ForbiddenResult(not hits, hits)


def contains_main(path: Path) -> bool:
    if not path.exists():
        return False
    stripped = _strip_comments_and_strings(path.read_text(encoding="utf-8", errors="replace"))
    return bool(re.search(r"\bmain\s*\(", stripped))


def scan_forbidden(path: Path, forbidden: list[str]) -> list[str]:
    result = scan_files(list(path.rglob("*.c")), forbidden)
    return [f"{file}: forbidden function {name}" for name, files in result.hits.items() for file in files]
