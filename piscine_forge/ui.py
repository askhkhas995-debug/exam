from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
from typing import Iterable, Sequence, TextIO

from .theme import Theme, color, colors_enabled, resolve_theme


UNICODE_SEPARATOR = "─"
ASCII_SEPARATOR = "-"

COMPACT_BANNER = """ ____  _____
|  _ \\|  ___|__  _ __ __ _  ___
| |_) | |_ / _ \\| '__/ _` |/ _ \\
|  __/|  _| (_) | | | (_| |  __/
|_|   |_|  \\___/|_|  \\__, |\\___|
                     |___/"""


@dataclass(frozen=True)
class RenderContext:
    theme: Theme
    color_enabled: bool = False
    unicode: bool = True


def _unicode_supported(stream: TextIO | None = None) -> bool:
    if os.environ.get("PFORGE_ASCII"):
        return False
    encoding = (getattr(stream, "encoding", None) or "").lower()
    if encoding and "ascii" in encoding:
        return False
    return True


def render_context(stream: TextIO | None = None, *, theme_name: str | None = None) -> RenderContext:
    theme = resolve_theme(theme_name)
    return RenderContext(theme=theme, color_enabled=colors_enabled(stream), unicode=_unicode_supported(stream))


def terminal_width(default: int = 80) -> int:
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except OSError:
        return default


def style(text: str, role: str, ctx: RenderContext | None = None) -> str:
    ctx = ctx or RenderContext(resolve_theme("plain"), color_enabled=False)
    return color(text, role, ctx.theme, enabled=ctx.color_enabled)


def format_kv(label: str, value: object, width: int = 15, ctx: RenderContext | None = None, role: str | None = None) -> str:
    value_text = str(value)
    if role:
        value_text = style(value_text, role, ctx)
    return f"{label:<{width}}: {value_text}"


def render_separator(title: str | None = None, width: int = 60, ctx: RenderContext | None = None) -> str:
    char = UNICODE_SEPARATOR if (ctx is None or ctx.unicode) else ASCII_SEPARATOR
    if title:
        return "\n".join([style(title, "title", ctx), style(char * len(title), "separator", ctx)])
    return style(char * width, "separator", ctx)


def render_banner(ctx: RenderContext | None = None) -> str:
    return style(COMPACT_BANNER, "title", ctx)


def render_menu(
    title: str,
    items: Sequence[tuple[str, str]],
    state: Sequence[tuple[str, object, str | None]] | None = None,
    *,
    ctx: RenderContext | None = None,
    subtitle: str = "Main menu",
) -> str:
    lines: list[str] = [render_separator(title, ctx=ctx), ""]
    if state:
        label_width = max(14, *(len(str(label)) for label, _value, _role in state))
        for label, value, role in state:
            lines.append(format_kv(label, value, label_width, ctx, role))
        lines.append("")
    lines.append(render_separator(subtitle, ctx=ctx))
    lines.append("")
    for key, text in items:
        key_text = f"{key:>3}" if key.isdigit() else f"{key:>3}"
        lines.append(f"{key_text}  {text}")
    return "\n".join(lines)


def render_progress_bar(done: int, total: int, width: int = 20) -> str:
    done = max(0, int(done))
    total = max(0, int(total))
    if total <= 0:
        filled = 0
        percent = 0
    else:
        done = min(done, total)
        filled = round((done / total) * width)
        percent = round((done / total) * 100)
    bar = "#" * filled + "-" * max(0, width - filled)
    return f"[{bar}] {done} / {total}  {percent}%"


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "not available"
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if not parts and secs:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    return ", ".join(parts) if parts else "0 seconds"


def status_marker(status: str | None, ctx: RenderContext | None = None) -> str:
    normalized = (status or "INFO").upper()
    role = {
        "OK": "success",
        "KO": "failure",
        "ERROR": "failure",
        "WARN": "warning",
        "WARNING": "warning",
        "INFO": "info",
    }.get(normalized, "muted")
    label = "WARN" if normalized == "WARNING" else normalized
    return style(f"[{label}]", role, ctx)


def render_section(title: str, rows: Iterable[str], *, ctx: RenderContext | None = None) -> list[str]:
    return [render_separator(title, ctx=ctx), "", *rows]
