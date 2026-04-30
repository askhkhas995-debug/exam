from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from .loader import load_yaml


@dataclass(frozen=True)
class NormResult:
    status: str
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status in {"OK", "SKIP"}


def check(root: Path, files: list[Path], enabled: bool) -> NormResult:
    config_path = root / "config" / "norm.yml"
    config = load_yaml(config_path).get("norm", {}) if config_path.exists() else {}
    if not enabled or not config.get("enabled", True):
        return NormResult("SKIP", [], reason="disabled")

    command = str(config.get("command", "norminette"))
    executable = shutil.which(command)
    if executable is None:
        return NormResult("SKIP", [command], reason="norminette command not found")

    cmd = [executable, *[str(path) for path in files]]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    status = "OK" if proc.returncode == 0 else "KO"
    return NormResult(status, cmd, proc.stdout, proc.stderr, proc.returncode)


def run_norminette(path: Path, command: str = "norminette") -> tuple[bool, str]:
    executable = shutil.which(command)
    if executable is None:
        return False, "norminette command not found"
    proc = subprocess.run([executable, str(path)], text=True, capture_output=True, timeout=10)
    return proc.returncode == 0, proc.stdout + proc.stderr
