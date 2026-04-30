from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping, TextIO


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass(frozen=True)
class Theme:
    name: str
    roles: dict[str, str]
    color: bool = True


THEMES: dict[str, Theme] = {
    "official": Theme(
        "official",
        {
            "title": "36;1",
            "header": "36",
            "separator": "90",
            "current": "33;1",
            "success": "32",
            "failure": "31",
            "warning": "33",
            "info": "36",
            "path": "36",
            "muted": "90",
            "normal": "0",
        },
    ),
    "tokyo-night": Theme(
        "tokyo-night",
        {
            "title": "36;1",
            "header": "34;1",
            "separator": "90",
            "current": "33;1",
            "success": "32;1",
            "failure": "31;1",
            "warning": "33",
            "info": "35",
            "path": "36",
            "muted": "90",
            "normal": "0",
        },
    ),
    "gruvbox": Theme(
        "gruvbox",
        {
            "title": "33;1",
            "header": "36",
            "separator": "90",
            "current": "33;1",
            "success": "32",
            "failure": "31",
            "warning": "33",
            "info": "36",
            "path": "36",
            "muted": "90",
            "normal": "0",
        },
    ),
    "plain": Theme("plain", {}, color=False),
}


ALIASES = {"graphbox": "gruvbox"}


def supports_color(stream: TextIO | None) -> bool:
    if stream is None:
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def resolve_theme(name: str | None = None) -> Theme:
    theme_name = (name or os.environ.get("PFORGE_THEME") or "official").strip().lower()
    theme_name = ALIASES.get(theme_name, theme_name)
    return THEMES.get(theme_name, THEMES["official"])


def colors_enabled(stream: TextIO | None = None, env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    theme = resolve_theme(env.get("PFORGE_THEME"))
    if not theme.color:
        return False
    if env.get("NO_COLOR"):
        return False
    return supports_color(stream)


def color(text: str, role: str, theme: Theme | str | None = None, enabled: bool = True) -> str:
    resolved = resolve_theme(theme if isinstance(theme, str) else (theme.name if theme else None))
    if not enabled or not resolved.color:
        return text
    code = resolved.roles.get(role)
    if not code:
        return text
    return f"\033[{code}m{text}\033[0m"


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)
