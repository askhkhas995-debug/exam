from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path
from typing import Any

from .correction_source import SourceResolution, render_source_lines
from .ui import RenderContext, format_kv, render_separator, status_marker

import yaml

PROJECT_LABELS = {
    "rush00": "Rush00",
    "rush01": "Rush01",
    "rush02": "Rush02",
    "sastantua": "Sastantua",
    "match_n_match": "Match-N-Match",
    "eval_expr": "Eval Expr",
    "bsq": "BSQ",
}

def load_legacy_metadata(repo, project_id: str) -> dict[str, Any]:
    slug = project_id.replace("-", "_").lower()
    meta_path = repo.root / "resources" / "legacy_subjects" / "projects" / slug / "subject.meta.yml"
    if not meta_path.exists():
        return {}
    try:
        with meta_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return {}

def project_display_name(subject_id: str) -> str:
    return PROJECT_LABELS.get(subject_id, subject_id.replace("_", " ").replace("-", " ").title())


def discover_piscine_projects(repo) -> list[dict[str, Any]]:
    try:
        pool = repo.get_pool("piscine42_default")
    except SystemExit:
        return []
    subjects = repo.subjects()
    project_ids: list[str] = []
    for module in pool.get("modules", []) or []:
        if module.get("id") == "projects":
            project_ids = [str(sid) for sid in module.get("subjects", []) or []]
            break
    projects: list[dict[str, Any]] = []
    for subject_id in project_ids:
        entry = subjects.get(subject_id)
        if not entry:
            continue
        meta = entry["meta"]
        if meta.get("type") != "project":
            continue
        projects.append(
            {
                "id": subject_id,
                "name": project_display_name(subject_id),
                "entry": entry,
                "meta": meta,
                "virtual": bool(entry.get("virtual")),
            }
        )
    return projects


def find_piscine_project(repo, project_id: str | None) -> dict[str, Any] | None:
    if not project_id:
        return None
    wanted = project_id.strip().lower().replace("-", "_")
    for project in discover_piscine_projects(repo):
        aliases = {
            str(project["id"]).lower(),
            str(project["id"]).lower().replace("-", "_"),
            str(project["name"]).lower(),
            str(project["name"]).lower().replace("-", "_").replace(" ", "_"),
        }
        if wanted in aliases:
            return project
    return None


def current_project(repo, state: dict | None) -> dict[str, Any] | None:
    state = state or {}
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0) or 0)
    if selected and 0 <= index < len(selected):
        return find_piscine_project(repo, selected[index].get("subject_id"))
    return None


def submission_contract(project: dict[str, Any]) -> dict[str, Any]:
    contract = dict(project.get("meta", {}).get("submission") or {})
    if not contract:
        contract = {"type": "generic_project", "status": "incomplete"}
    contract.setdefault("type", "generic_project")
    return contract


def contract_is_complete(contract: dict[str, Any]) -> bool:
    return str(contract.get("status", "")).lower() != "incomplete"


def _project_slug(project_id: str) -> str:
    return project_id.replace("-", "_").lower()


def _legacy_path(repo, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return None
    candidate = (repo.root / path).resolve()
    if not candidate.is_relative_to(repo.root):
        return None
    return candidate


def _reference_file_status(repo, meta: dict[str, Any], key: str) -> str:
    raw_path = (meta.get("subject_pdf") or {}).get(key)
    path = _legacy_path(repo, raw_path)
    return "available" if path and path.exists() else "missing"


def _local_tests_status(project: dict[str, Any], repo) -> str:
    tests_path = repo.root / "corrections" / "projects" / project["id"] / "tests.yml"
    if not tests_path.exists():
        return "missing"
    try:
        with tests_path.open(encoding="utf-8") as f:
            tests = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return "missing"
    fixed_tests = tests.get("fixed_tests") or []
    return "configured" if fixed_tests else "missing"


def _correction_status(project: dict[str, Any], repo) -> str:
    contract = submission_contract(project)
    if not contract_is_complete(contract):
        return "metadata incomplete"
    if str(contract.get("status", "")).lower() == "local_tests_configured" and _local_tests_status(project, repo) == "configured":
        return "local trainer"
    return "preflight only"


def render_project_list(repo, *, ctx: RenderContext | None = None) -> str:
    lines = [render_separator("Projects", ctx=ctx), "", "Piscine Projects"]
    projects = discover_piscine_projects(repo)
    if not projects:
        lines.append("  - none configured")
    for index, project in enumerate(projects, start=1):
        lines.append(f"{index:>3}  {project['name']}")
    lines.extend(["", "  0  Back"])
    return "\n".join(lines)


def render_project_detail(project: dict[str, Any], rendu: Path, *, ctx: RenderContext | None = None) -> str:
    lines = [
        render_separator("Project", ctx=ctx),
        "",
        format_kv("Name", project["name"], ctx=ctx),
        format_kv("Type", "Piscine project", ctx=ctx),
        format_kv("Correction", "Project Moulinette", ctx=ctx),
        format_kv("Rendu", rendu.as_posix(), ctx=ctx, role="path"),
        "",
        render_separator("Actions", ctx=ctx),
        "",
        "  1  Continue / Start",
        "  2  Requirements",
        "  3  Check submission",
        "  4  Run correction",
        "  0  Back",
    ]
    return "\n".join(lines)


def render_project_requirements(project: dict[str, Any], repo, *, ctx: RenderContext | None = None) -> str:
    contract = submission_contract(project)
    legacy_meta = load_legacy_metadata(repo, project["id"])
    correction_status = _correction_status(project, repo)
    local_tests = _local_tests_status(project, repo)

    lines = [
        render_separator("Project Requirements", ctx=ctx),
        "",
        format_kv("Project", _project_slug(str(project["id"])), ctx=ctx),
        format_kv("Mode", "local trainer", ctx=ctx),
    ]

    lines.append(format_kv("Built-in subject", "available" if project.get("entry") else "missing", ctx=ctx))
    lines.append(format_kv("Reference PDF", _reference_file_status(repo, legacy_meta, "local_pdf_path"), ctx=ctx))
    lines.append(format_kv("Reference text", _reference_file_status(repo, legacy_meta, "local_text_path"), ctx=ctx))
    lines.append(format_kv("Local tests", local_tests, ctx=ctx))
    lines.append(format_kv("Correction status", correction_status, ctx=ctx))
    lines.append(format_kv("Submission contract", "configured" if contract_is_complete(contract) else "missing", ctx=ctx))
    lines.append(format_kv("Official 42 services", "not connected", ctx=ctx))
    lines.append(format_kv("Remote downloads", "disabled", ctx=ctx))
    lines.append("")

    if not contract_is_complete(contract):
        lines.extend(
            [
                "This project is listed, but detailed submission requirements are not fully configured yet.",
                "",
                render_separator("Limitations", ctx=ctx),
                "",
                "Project Moulinette is a local trainer, not official 42 Moulinette.",
                "",
                render_separator("Next", ctx=ctx),
                "",
                "Add a submission contract to the project metadata before enabling strict checks.",
            ]
        )
        return "\n".join(lines)

    required = [str(item) for item in contract.get("required_files", []) or []]
    allowed = [str(item) for item in contract.get("allowed_patterns", []) or []]
    forbidden = [str(item) for item in contract.get("forbidden_files", []) or []]
    binary = contract.get("expected_binary")
    lines.extend([render_separator("Limitations", ctx=ctx), "", "Project Moulinette is a local trainer, not official 42 Moulinette.", ""])
    lines.extend([render_separator("Required", ctx=ctx), ""])
    lines.extend([f"  {item}" for item in required] or ["  not configured"])
    if allowed:
        lines.extend(["", render_separator("Allowed patterns", ctx=ctx), ""])
        lines.extend(f"  {item}" for item in allowed)
    if binary:
        lines.extend(["", render_separator("Expected binary", ctx=ctx), "", f"  {binary}"])
    lines.extend(["", render_separator("Local checks", ctx=ctx), "", "  make"])
    if binary:
        lines.append(f"  ./{binary} <maps>")
    lines.extend(["", render_separator("Forbidden", ctx=ctx), ""])
    lines.extend([f"  {item}" for item in forbidden] or ["  not configured"])
    return "\n".join(lines)


def render_project_references(repo, project_id: str | None = None, *, ctx: RenderContext | None = None) -> str:
    catalog = "resources/legacy_subjects/references.yml"
    lines = [
        render_separator("Project References", ctx=ctx),
        "",
        format_kv("Catalog", catalog, ctx=ctx, role="path"),
        format_kv("Purpose", "local reference catalog only", ctx=ctx),
        format_kv("Remote downloads", "disabled", ctx=ctx),
        "",
    ]

    ref_path = repo.root / "resources" / "legacy_subjects" / "references.yml"
    if not ref_path.exists():
        return "\n".join(lines) + "No references catalog found."

    try:
        with ref_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        return "\n".join(lines) + f"Error loading references: {e}"

    refs = data.get("external_references", [])
    if project_id:
        slug = _project_slug(project_id)
        refs = [r for r in refs if slug in r.get("projects", [])]
        lines.append(format_kv("Filter", slug, ctx=ctx))
        lines.append("")

    if not refs:
        lines.append("No references found.")
        return "\n".join(lines)

    for ref in refs:
        projects = ", ".join(str(project) for project in ref.get("projects", []) or [])
        lines.append(format_kv("Reference ID", ref.get("id", "unknown"), ctx=ctx))
        lines.append(format_kv("Repository", ref.get("repo", "unknown"), ctx=ctx))
        lines.append(format_kv("URL", ref.get("repo_url", "unknown"), ctx=ctx))
        lines.append(format_kv("Projects", projects or "none", ctx=ctx))
        policies = ref.get("usage_policy", [])
        lines.append(format_kv("Policy", ", ".join(policies) if policies else "none", ctx=ctx))
        lines.append("")

    return "\n".join(lines)



def _copy_local_pdf(pdf_path: Path, copy_to: str) -> tuple[int, str]:
    requested = Path(copy_to).expanduser()
    if requested.exists() and requested.is_dir():
        destination = requested / "subject.pdf"
    elif requested.suffix.lower() == ".pdf":
        destination = requested
    else:
        requested.mkdir(parents=True, exist_ok=True)
        destination = requested / "subject.pdf"
    if destination.exists():
        return 1, f"destination exists; not overwritten: {destination.as_posix()}"
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, destination)
    except OSError as exc:
        return 1, f"copy failed: {exc}"
    return 0, f"copied to {destination.as_posix()}"


def render_project_subject_result(
    repo,
    project_id: str,
    copy_to: str | None = None,
    *,
    ctx: RenderContext | None = None,
) -> tuple[int, str]:
    lines = [render_separator("Project Subject", ctx=ctx), ""]
    slug = _project_slug(project_id)
    meta = load_legacy_metadata(repo, project_id)

    if not meta:
        lines.append(f"No local legacy metadata found for '{project_id}'.")
        return 1, "\n".join(lines)

    lines.append(format_kv("Project", slug, ctx=ctx))
    pdf_info = meta.get("subject_pdf", {})
    pdf_rel_path = str(pdf_info.get("local_pdf_path") or f"resources/legacy_subjects/projects/{slug}/subject.pdf")
    text_rel_path = str(pdf_info.get("local_text_path") or f"resources/legacy_subjects/projects/{slug}/subject.txt")
    pdf_path = _legacy_path(repo, pdf_rel_path)
    text_path = _legacy_path(repo, text_rel_path)
    pdf_exists = bool(pdf_path and pdf_path.exists())
    text_exists = bool(text_path and text_path.exists())

    lines.append(format_kv("Reference PDF", "available" if pdf_exists else "missing", ctx=ctx))
    if pdf_exists:
        lines.append(format_kv("Local PDF path", pdf_rel_path, ctx=ctx, role="path"))
    else:
        lines.append(format_kv("Expected local path", pdf_rel_path, ctx=ctx, role="path"))
    lines.append(format_kv("Reference text", "available" if text_exists else "missing", ctx=ctx))
    if text_exists:
        lines.append(format_kv("Local text path", text_rel_path, ctx=ctx, role="path"))
    lines.append(format_kv("Remote downloads", "disabled", ctx=ctx))

    exit_code = 0
    if pdf_exists:
        if copy_to:
            copy_code, message = _copy_local_pdf(pdf_path, copy_to)
            exit_code = copy_code
            lines.append(format_kv("Copy", message, ctx=ctx))
    else:
        if copy_to:
            exit_code = 1
            lines.append(format_kv("Copy", "failed; local reference PDF is missing", ctx=ctx))
        lines.append("Note: add the PDF manually if you want a local reference copy.")

    return exit_code, "\n".join(lines)


def render_project_subject(repo, project_id: str, copy_to: str | None = None, *, ctx: RenderContext | None = None) -> str:
    return render_project_subject_result(repo, project_id, copy_to, ctx=ctx)[1]

def _all_submission_files(rendu: Path) -> tuple[list[Path], str | None]:

    if not rendu.exists():
        return [], None
    files: list[Path] = []
    for path in sorted(rendu.rglob("*")):
        rel = path.relative_to(rendu)
        if path.is_symlink():
            return [], f"unsafe symlink rejected: {rel.as_posix()}"
        if path.is_dir():
            continue
        files.append(rel)
    return files, None


def _matches(rel: Path, patterns: list[str]) -> bool:
    text = rel.as_posix()
    return any(fnmatch.fnmatch(text, pattern) or text == pattern for pattern in patterns)


def _display_rendu(rendu: Path) -> str:
    text = rendu.as_posix()
    marker = "/workspace/rendu"
    if text.endswith(marker):
        return "workspace/rendu/"
    if text.endswith("workspace/rendu"):
        return "workspace/rendu/"
    return text


def _check_submission(project: dict[str, Any], rendu: Path) -> dict[str, Any]:
    contract = submission_contract(project)
    if not contract_is_complete(contract):
        return {"status": "incomplete", "reason": "metadata incomplete", "checks": {}, "contract": contract}

    files, error = _all_submission_files(rendu)
    if error:
        return {"status": "KO", "reason": error, "hint": "Remove unsafe symlinks from workspace/rendu/", "checks": {}, "contract": contract}
    if not files:
        return {
            "status": "KO",
            "reason": "Nothing turned in",
            "hint": "Put your project files in workspace/rendu/",
            "checks": {},
            "contract": contract,
        }

    required = [str(item) for item in contract.get("required_files", []) or []]
    forbidden = [str(item) for item in contract.get("forbidden_files", []) or []]
    allowed = [str(item) for item in contract.get("allowed_patterns", []) or []]
    binary = contract.get("expected_binary")
    allow_extra = bool(contract.get("allow_extra_files", True))

    actual = {rel.as_posix() for rel in files}
    missing = [item for item in required if item not in actual]
    forbidden_hits = [rel.as_posix() for rel in files if _matches(rel, forbidden)]
    makefile_ok = "Makefile" in actual if contract.get("makefile_required") else True
    binary_ok = True if not binary else str(binary) in actual
    disallowed = []
    if not allow_extra:
        allowed_set = set(required)
        disallowed = [
            rel.as_posix()
            for rel in files
            if rel.as_posix() not in allowed_set and not _matches(rel, allowed)
        ]

    checks = {
        "required files": "OK" if not missing else "KO",
        "forbidden files": "OK" if not forbidden_hits else "KO",
        "makefile": "OK" if makefile_ok else "KO",
    }
    if binary:
        checks["binary"] = "OK" if binary_ok else "KO"
    if not allow_extra:
        checks["extra files"] = "OK" if not disallowed else "KO"

    reason = ""
    hint = ""
    if missing:
        reason = f"Required file `{missing[0]}` is missing."
        hint = "Put the required project files in workspace/rendu/"
    elif forbidden_hits:
        reason = f"Forbidden file found: {forbidden_hits[0]}"
        hint = "Remove build artifacts, correction files, or test folders from workspace/rendu/"
    elif not makefile_ok:
        reason = "Makefile is required."
        hint = "Add a Makefile to workspace/rendu/"
    elif binary and not binary_ok:
        reason = f"Expected binary `{binary}` was not found after build."
        hint = "Run `make` inside workspace/rendu/ and fix build errors."
    elif disallowed:
        reason = f"Unexpected file found: {disallowed[0]}"
        hint = "Remove files not allowed by the submission contract."

    status = "OK" if not reason else "KO"
    return {
        "status": status,
        "reason": reason,
        "hint": hint,
        "checks": checks,
        "contract": contract,
        "files": sorted(actual),
    }


def render_project_submission_check(
    project: dict[str, Any],
    rendu: Path,
    *,
    source: SourceResolution | None = None,
    ctx: RenderContext | None = None,
) -> str:
    result = _check_submission(project, rendu)
    lines = [render_separator("Submission Check", ctx=ctx), ""]
    lines.append(format_kv("Project", project["name"], ctx=ctx))
    if source and source.is_vogsphere:
        lines.extend(render_source_lines(source, ctx=ctx))
    else:
        lines.append(format_kv("Rendu", _display_rendu(rendu), ctx=ctx, role="path"))
    if result["status"] == "incomplete":
        lines.append(format_kv("Status", "metadata incomplete", ctx=ctx))
        lines.extend(["", "Cannot run strict submission check yet."])
        return "\n".join(lines)
    lines.append(format_kv("Status", status_marker(result["status"], ctx), ctx=ctx))
    checks = result.get("checks") or {}
    if checks:
        lines.extend(["", render_separator("Checks", ctx=ctx), ""])
        for name, status in checks.items():
            lines.append(format_kv(name, status_marker(status, ctx), ctx=ctx))
    if result.get("reason"):
        lines.extend(["", render_separator("Reason", ctx=ctx), "", str(result["reason"])])
    if result.get("hint"):
        lines.extend(["", render_separator("Hint", ctx=ctx), "", str(result["hint"])])
    return "\n".join(lines)
