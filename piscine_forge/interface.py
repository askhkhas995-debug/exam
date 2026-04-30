from __future__ import annotations

import os
from pathlib import Path
import sys

from . import __version__
from .correction_ux import (
    correction_label,
    current_item_label,
    display_mode,
    render_correction_result,
)
from .curriculum import (
    current_curriculum_context,
    curriculum_modules,
    exam_context,
    exam_display_name,
    exercise_label,
    module_label,
    pool_display_name,
)
from .doctor import render_doctor
from .evaluators import evaluate_subject
from .exam_ui import render_exam_levels, render_exam_rules, render_exam_screen, render_exam_setup, render_exam_started
from .exam_ui import EXAM_GROUP_ORDER
from .loader import Repository
from .picker import curriculum_sequence, pick_from_pool
from .progress import (
    format_current,
    init_curriculum_progress,
    init_exam_progress,
    load_progress,
    record_attempt,
    summarize_module_progress,
    summarize_history,
    summarize_progress,
)
from .reset import ResetCancelled, reset_all, reset_progress, reset_session, reset_traces
from .session import Session
from .trace import latest_trace, read_trace, summarize_trace, write_trace_bundle
from .projects import (
    discover_piscine_projects,
    project_display_name,
    render_project_detail,
    render_project_list,
    render_project_requirements,
    render_project_submission_check,
)
from .ui import render_banner, render_menu, render_separator, render_context
from .vogsphere import (
    commit_repo,
    default_repo_name,
    history_lines,
    init_repo,
    log_lines,
    push_repo,
    render_status,
    submit_repo,
)


def _emit(output, text: str = "") -> None:
    output(text)


def _ctx(output=print):
    return render_context(sys.stdout if output is print else None)


def _ask(input_func, prompt: str = "Choose: ") -> str:
    try:
        return input_func(prompt).strip()
    except EOFError:
        return "0"


def _choice(input_func, max_choice: int) -> str:
    return _ask(input_func, f"Choose [0-{max_choice}]: ")


def _pause(input_func) -> None:
    try:
        input_func("Press Enter to continue...")
    except EOFError:
        return


def _pool_duration(pool: dict) -> int | None:
    minutes = pool.get("duration_minutes")
    return int(minutes) * 60 if minutes is not None else None


def show_main_menu(repo: Repository, session: Session, output=print) -> None:
    ctx = _ctx(output)
    state = session.load_if_exists()
    mode = "none"
    state_rows: list[tuple[str, object, str | None]] = [("Mode", mode, None)]
    if state:
        mode = display_mode(state)
        state_rows = [("Mode", mode, None)]
        if state.get("mode") == "exam":
            info = exam_context(repo, state)
            state_rows.extend(
                [
                    ("Exam", f"{info['exam']} ({info['pool_id']})", None),
                    ("Level", f"{info['level']} / {info['level_count']}", None),
                    ("Exercise", info["subject_id"], None),
                    ("Correction", correction_label(state), None),
                ]
            )
        elif state.get("mode") == "curriculum":
            progress = load_progress(repo.root)
            info = current_curriculum_context(repo, state, progress)
            state_rows.extend(
                [
                    ("Pool", info["pool_id"], None),
                    ("Module", f"{info['module']} ({info['module_id']})", None),
                    ("Exercise", info["exercise_id"], None),
                    ("Subject", info["subject_id"], None),
                    ("Correction", correction_label(state), None),
                    ("Next", info["next_subject_id"], None),
                ]
            )
        elif state.get("mode") == "project":
            selected = state.get("selected", [])
            index = int(state.get("current_index", 0))
            active = selected[index].get("subject_id", "") if selected and 0 <= index < len(selected) else ""
            state_rows.extend(
                [
                    ("Project", project_display_name(active) if active else "none", None),
                    ("Correction", correction_label(state), None),
                ]
            )
        else:
            selected = state.get("selected", [])
            index = int(state.get("current_index", 0))
            active = selected[index].get("subject_id", "") if selected and 0 <= index < len(selected) else ""
            state_rows.append((current_item_label(state), active or "none", None))
    state_rows.append(("Rendu", session.rendu_dir.relative_to(repo.root), "path"))
    if state:
        if state.get("mode") == "exam":
            items = [
                ("1", "Continue"),
                ("2", "Run Grademe"),
                ("3", "Exam status"),
                ("4", "Trace"),
                ("5", "Exams"),
                ("6", "Projects"),
                ("7", "Vogsphere"),
                ("8", "Tools"),
                ("0", "Exit"),
            ]
        else:
            items = [
                ("1", "Continue"),
                ("2", f"Run {correction_label(state)}"),
                ("3", "Status"),
                ("4", "Trace"),
                ("5", "Piscines"),
                ("6", "Projects"),
                ("7", "Vogsphere"),
                ("8", "Tools"),
                ("0", "Exit"),
            ]
    else:
        items = [
            ("1", "Piscines"),
            ("2", "Exams"),
            ("3", "Projects"),
            ("4", "Vogsphere"),
            ("5", "Tools"),
            ("0", "Exit"),
        ]
    menu = render_menu(
        "PiscineForge",
        items,
        state_rows,
        ctx=ctx,
    )
    _emit(output, "")
    if os.environ.get("PFORGE_BANNER", "compact").lower() not in {"0", "false", "no", "off"}:
        for line in render_banner(ctx).splitlines():
            _emit(output, line)
        _emit(output, "")
    for line in menu.splitlines():
        _emit(output, line)
    _emit(output, "")


def run_menu(repo: Repository | None = None, *, input_func=input, output=print) -> int:
    repo = repo or Repository(Path.cwd())
    session = Session(repo.root)
    session.ensure()
    while True:
        show_main_menu(repo, session, output)
        state = session.load_if_exists()
        choice = _choice(input_func, 8 if state else 5)
        if choice == "0":
            return 0
        if not state:
            if choice == "1":
                choose_piscine(repo, session, input_func, output)
            elif choice == "2":
                choose_exam(repo, session, input_func, output)
            elif choice == "3":
                choose_project(repo, session, input_func, output)
            elif choice == "4":
                show_vogsphere(repo, session, input_func, output)
            elif choice == "5":
                show_tools(repo, session, input_func, output)
            else:
                _emit(output, "Unknown choice.")
            continue
        if choice == "1":
            if state.get("mode") == "exam":
                show_exam_terminal(repo, session, input_func, output)
            else:
                show_current(repo, session, output)
                _pause(input_func)
        elif choice == "2":
            run_correction_from_menu(repo, session, output)
            _pause(input_func)
        elif choice == "3":
            show_progress(repo, session, output)
            _pause(input_func)
        elif choice == "4":
            show_trace(repo, session, output)
            _pause(input_func)
        elif choice == "5":
            if state.get("mode") == "exam":
                choose_exam(repo, session, input_func, output)
            else:
                choose_piscine(repo, session, input_func, output)
        elif choice == "6":
            choose_project(repo, session, input_func, output)
        elif choice == "7":
            show_vogsphere(repo, session, input_func, output)
        elif choice == "8":
            show_tools(repo, session, input_func, output)
        else:
            _emit(output, "Unknown choice.")


def show_tools(repo: Repository, session: Session, input_func=input, output=print) -> None:
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_separator("Tools", ctx=ctx))
        _emit(output, "")
        _emit(output, "  1  Doctor / Setup check")
        _emit(output, "  2  Validate repository")
        _emit(output, "  3  History")
        _emit(output, "  4  Reset")
        _emit(output, "  5  Version")
        _emit(output, "  0  Back")
        _emit(output, "")
        choice = _ask(input_func)
        if choice == "0":
            return
        if choice == "1":
            text, _code = render_doctor(repo, session, ctx=ctx)
            _emit(output, text)
            _pause(input_func)
        elif choice == "2":
            _validate(repo, output)
            _pause(input_func)
        elif choice == "3":
            show_history(repo, session, output)
            _pause(input_func)
        elif choice == "4":
            show_reset_tools(session, input_func, output)
        elif choice == "5":
            _emit(output, f"PiscineForge {__version__}")
            _pause(input_func)
        else:
            _emit(output, "Invalid choice.")


def show_reset_tools(session: Session, input_func=input, output=print) -> None:
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_separator("Reset", ctx=ctx))
        _emit(output, "")
        _emit(output, "  1  Session")
        _emit(output, "  2  Progress")
        _emit(output, "  3  Traces")
        _emit(output, "  4  All generated state")
        _emit(output, "  0  Back")
        _emit(output, "")
        choice = _ask(input_func)
        if choice == "0":
            return
        try:
            if choice == "1":
                deleted = reset_session(session)
                label = "session"
            elif choice == "2":
                deleted = reset_progress(session, input_func=input_func)
                label = "progress"
            elif choice == "3":
                deleted = reset_traces(session, input_func=input_func)
                label = "traces"
            elif choice == "4":
                deleted = reset_all(session, input_func=input_func)
                label = "all"
            else:
                _emit(output, "Invalid choice.")
                continue
        except ResetCancelled as exc:
            _emit(output, str(exc))
            _pause(input_func)
            continue
        _emit(output, f"reset {label}: {len(deleted)} item(s)")
        _pause(input_func)


def _select_from_list(
    title: str,
    items: list[tuple[str, str]],
    input_func,
    output=print,
    *,
    page_size: int = 20,
) -> str | None:
    ctx = _ctx(output)
    page = 0
    while True:
        start = page * page_size
        chunk = items[start : start + page_size]
        _emit(output, "")
        _emit(output, render_separator(title, ctx=ctx))
        _emit(output, "")
        if not items:
            _emit(output, "No items available.")
            _pause(input_func)
            return None
        for index, (label, detail) in enumerate(chunk, start=1):
            suffix = f" - {detail}" if detail else ""
            _emit(output, f"{index:>3}  {label}{suffix}")
        if start + page_size < len(items):
            _emit(output, "n. Next page")
        if page > 0:
            _emit(output, "p. Previous page")
        _emit(output, "0. Back")
        _emit(output, "")
        choice = _ask(input_func)
        if choice == "0":
            return None
        if choice.lower() == "n" and start + page_size < len(items):
            page += 1
            continue
        if choice.lower() == "p" and page > 0:
            page -= 1
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(chunk):
            return chunk[int(choice) - 1][0]
        _emit(output, "Invalid choice.")


def choose_piscine(repo: Repository, session: Session, input_func=input, output=print) -> None:
    pools: list[tuple[str, str, str]] = []
    for pool_id, entry in sorted(repo.pools().items()):
        pool = entry["pool"]
        if pool.get("kind") == "curriculum" and pool_id.startswith("piscine"):
            count = sum(len(module.get("subjects", [])) for module in pool.get("modules", []))
            modules = len(pool.get("modules", []) or [])
            label = f"{pool_display_name(pool_id, pool)} ({pool_id})"
            pools.append((pool_id, label, f"{modules} modules / {count} exercises - explicit pool order"))
    ctx = _ctx(output)
    _emit(output, "")
    _emit(output, render_separator("Piscines", ctx=ctx))
    _emit(output, "")
    for index, (_pool_id, label, detail) in enumerate(pools, start=1):
        _emit(output, f"{index:>3}  {label} - {detail}")
    _emit(output, "  0  Back")
    _emit(output, "")
    choice = _ask(input_func)
    if choice == "0":
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(pools)):
        _emit(output, "Invalid choice.")
        _pause(input_func)
        return
    pool_id = pools[int(choice) - 1][0]
    choose_piscine_action(repo, session, pool_id, input_func, output)


def _resume_index(repo: Repository, pool_id: str, selected: list[dict]) -> int:
    progress = load_progress(repo.root)
    completed = set(progress.get("curricula", {}).get(pool_id, {}).get("completed", []) or [])
    for index, item in enumerate(selected):
        if item.get("subject_id") not in completed:
            return index
    return max(0, len(selected) - 1)


def _start_curriculum_at(
    repo: Repository,
    session: Session,
    pool_id: str,
    selected: list[dict],
    index: int,
    reason: str,
    output=print,
) -> None:
    pool = repo.get_pool(pool_id)
    state = session.start(
        repo,
        pool_id=pool_id,
        kind="piscine",
        selected=selected,
        current_index=index,
        selection_reason=reason,
    )
    init_curriculum_progress(repo, session.root, pool_id, state["selected"][state["current_index"]]["subject_id"], state)
    info = current_curriculum_context(repo, state, load_progress(repo.root))
    _emit(output, f"Started {pool_id}: {info['module']}/{info['exercise_id']} {info['subject_id']}")
    _emit(output, f"Reason: {info['reason']}")
    _emit(output, f"Next: {info['next_subject_id']}")


def choose_piscine_action(repo: Repository, session: Session, pool_id: str, input_func=input, output=print) -> None:
    pool = repo.get_pool(pool_id)
    selected = curriculum_sequence(pool)
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_separator(pool_display_name(pool_id, pool), ctx=ctx))
        _emit(output, "")
        _emit(output, f"Pool: {pool_id}")
        _emit(output, f"Modules: {len(pool.get('modules', []) or [])}")
        _emit(output, f"Exercises: {len(selected)}")
        _emit(output, "")
        _emit(output, "  1  Resume progress")
        _emit(output, "  2  Start from beginning")
        _emit(output, "  3  Browse modules")
        _emit(output, "  0  Back")
        _emit(output, "")
        choice = _ask(input_func)
        if choice == "0":
            return
        if choice == "1":
            index = _resume_index(repo, pool_id, selected)
            progress = load_progress(repo.root)
            completed = progress.get("curricula", {}).get(pool_id, {}).get("completed", []) or []
            reason = "previous exercises completed" if completed else "first exercise in module"
            _start_curriculum_at(repo, session, pool_id, selected, index, reason, output)
            _pause(input_func)
            return
        if choice == "2":
            _start_curriculum_at(repo, session, pool_id, selected, 0, "first exercise in module", output)
            _pause(input_func)
            return
        if choice == "3":
            chosen = choose_curriculum_module_exercise(repo, pool_id, input_func, output)
            if chosen is not None:
                _start_curriculum_at(repo, session, pool_id, selected, chosen, "selected from module browser", output)
                _pause(input_func)
                return
            continue
        _emit(output, "Invalid choice.")


def choose_curriculum_module_exercise(repo: Repository, pool_id: str, input_func=input, output=print) -> int | None:
    pool = repo.get_pool(pool_id)
    modules = curriculum_modules(pool)
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_separator(pool_display_name(pool_id, pool), ctx=ctx))
        _emit(output, "")
        numbered: list[dict] = []
        for number, module in enumerate(modules, start=1):
            subjects = module.get("subjects", []) or []
            _emit(output, f"{number:>3}  {module_label(module.get('id')):<10} {len(subjects)} exercises")
            numbered.append(module)
        _emit(output, "  0  Back")
        _emit(output, "")
        choice = _ask(input_func)
        if choice == "0":
            return None
        if not choice.isdigit() or not (1 <= int(choice) <= len(numbered)):
            _emit(output, "Invalid choice.")
            continue
        module = numbered[int(choice) - 1]
        result = choose_exercise_in_module(repo, pool, module, input_func, output)
        if result is not None:
            return result


def choose_exercise_in_module(repo: Repository, pool: dict, module: dict, input_func=input, output=print) -> int | None:
    del repo
    ctx = _ctx(output)
    subjects = [str(sid) for sid in module.get("subjects", []) or []]
    module_id = module.get("id")
    while True:
        _emit(output, "")
        _emit(output, render_separator(module_label(module_id), ctx=ctx))
        _emit(output, "")
        for index, subject_id in enumerate(subjects, start=1):
            _emit(output, f"{index:>3}  {exercise_label(index - 1)} {subject_id}")
        _emit(output, "  0  Back")
        _emit(output, "")
        choice = _ask(input_func)
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(subjects):
            selected_subject = subjects[int(choice) - 1]
            sequence = curriculum_sequence(pool)
            for index, item in enumerate(sequence):
                if item.get("module") == module_id and item.get("subject_id") == selected_subject:
                    return index
        _emit(output, "Invalid choice.")
    _pause(input_func)


def choose_exam(repo: Repository, session: Session, input_func=input, output=print) -> None:
    pool_id = _select_exam_by_group(repo, input_func, output)
    if not pool_id:
        return
    seed = confirm_exam_start(repo, pool_id, input_func, output)
    if seed == "cancel":
        return
    pool = repo.get_pool(pool_id)
    selected = pick_from_pool(pool, seed=seed)
    state = session.start(
        repo,
        pool_id=pool_id,
        kind="exam",
        selected=selected,
        seed=seed,
        duration_seconds=_pool_duration(pool),
    )
    init_exam_progress(session.root, pool_id, seed, selected, state)
    _emit(output, render_exam_started(repo, state, ctx=_ctx(output)))
    _pause(input_func)


def confirm_exam_start(repo: Repository, pool_id: str, input_func=input, output=print) -> int | None | str:
    pool = repo.get_pool(pool_id)
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_exam_setup(pool_id, pool, ctx=ctx))
        _emit(output, "")
        choice = _choice(input_func, 4)
        if choice == "1":
            return None
        if choice == "2":
            seed = _read_seed(input_func, output)
            return seed
        if choice == "3":
            _emit(output, "")
            _emit(output, render_exam_levels(pool_id, pool, ctx=ctx))
            _pause(input_func)
            continue
        if choice == "4":
            _emit(output, "")
            _emit(output, render_exam_rules(ctx=ctx))
            _pause(input_func)
            continue
        if choice == "0":
            return "cancel"
        _emit(output, "Invalid choice.")


def _exam_group(pool_id: str, pool: dict) -> str:
    if pool.get("group"):
        return str(pool["group"])
    text = " ".join(
        str(value).lower()
        for value in [pool_id, pool.get("origin", ""), pool.get("version", ""), pool.get("mode", "")]
    )
    if "revanced" in text:
        return "Imported Practice"
    if "rank" in text:
        return "Rank Practice"
    if "handwritten" in text:
        return "Handwritten Practice"
    if "grademe" in text:
        return "Grademe-style"
    if "1337" in text or "legacy" in text:
        return "Legacy Practice"
    if "classic" in text or "examshell" in text:
        return "ExamShell-style Practice"
    return "Imported Practice"


def _exam_display_label(pool_id: str, pool: dict) -> str:
    name = str(pool.get("display_name") or pool_id)
    return f"{name} ({pool_id})" if name != pool_id else name


def _exam_level_text(pool: dict) -> str:
    levels_count = pool.get("levels_count")
    if levels_count is None:
        levels_count = len(pool.get("levels", []) or [])
    if not levels_count:
        return ""
    return f"{int(levels_count)} level{'s' if int(levels_count) != 1 else ''}"


def _exam_description(pool: dict) -> str:
    return str(pool.get("description") or pool.get("mode") or "").strip()


def _select_exam_by_group(repo: Repository, input_func, output=print) -> str | None:
    ctx = _ctx(output)
    grouped: dict[str, list[tuple[str, str, str, str]]] = {
        "ExamShell-style Practice": [],
        "Rank Practice": [],
        "Handwritten Practice": [],
        "Imported Practice": [],
        "Legacy Practice": [],
    }
    for pool_id, entry in sorted(repo.pools().items()):
        pool = entry["pool"]
        if pool.get("kind") != "exam":
            continue
        grouped.setdefault(_exam_group(pool_id, pool), []).append(
            (pool_id, _exam_display_label(pool_id, pool), _exam_level_text(pool), _exam_description(pool))
        )

    numbered: list[tuple[str, str]] = []
    _emit(output, "")
    _emit(output, render_separator("Exams", ctx=ctx))
    _emit(output, "")
    number = 1
    for group in EXAM_GROUP_ORDER:
        items = grouped.get(group, [])
        if not items:
            continue
        _emit(output, group)
        label_width = max(len(label) for _pool_id, label, _level_text, _description in items)
        for pool_id, label, level_text, description in items:
            suffix = f"  {level_text}" if level_text else ""
            _emit(output, f"{number:>3}  {label:<{label_width}}{suffix}")
            if description:
                _emit(output, f"     {description}")
            numbered.append((pool_id, description))
            number += 1
        _emit(output, "")
    _emit(output, "  0  Back")
    _emit(output, "")
    choice = _ask(input_func)
    if choice == "0":
        return None
    if not choice.isdigit() or not (1 <= int(choice) <= len(numbered)):
        _emit(output, "Invalid choice.")
        _pause(input_func)
        return None
    return numbered[int(choice) - 1][0]


def _read_seed(input_func, output=print) -> int | None | str:
    text = _ask(input_func, "Seed (blank for random, 0 to cancel): ")
    if text == "0":
        return "cancel"
    if not text:
        return None
    try:
        seed = int(text)
    except ValueError:
        _emit(output, "Invalid seed. Use an integer or leave it blank.")
        _pause(input_func)
        return "cancel"
    if seed < 0:
        _emit(output, "Invalid seed. Use zero or a positive integer.")
        _pause(input_func)
        return "cancel"
    return seed


def choose_project(repo: Repository, session: Session, input_func=input, output=print) -> None:
    projects = discover_piscine_projects(repo)
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_project_list(repo, ctx=ctx))
        _emit(output, "")
        choice = _choice(input_func, len(projects))
        if choice == "0":
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(projects)):
            _emit(output, "Invalid choice.")
            continue
        show_project_detail(repo, session, projects[int(choice) - 1], input_func, output)


def _rendu_label(repo: Repository, session: Session) -> Path:
    try:
        return session.rendu_dir.relative_to(repo.root)
    except ValueError:
        return session.rendu_dir


def _start_project_session(repo: Repository, session: Session, project: dict, output=print) -> dict:
    subject_id = str(project["id"])
    session.set_current_subject(repo, subject_id)
    state = session.load()
    state["pool_id"] = "projects"
    state["kind"] = "project"
    state["mode"] = "project"
    state["selection_reason"] = "selected from projects menu"
    state["module_id"] = "projects"
    session.save(state)
    _emit(output, f"Started project: {project['name']} ({subject_id})")
    return session.load()


def show_project_detail(repo: Repository, session: Session, project: dict, input_func=input, output=print) -> None:
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_project_detail(project, _rendu_label(repo, session), ctx=ctx))
        _emit(output, "")
        choice = _choice(input_func, 4)
        if choice == "0":
            return
        if choice == "1":
            _start_project_session(repo, session, project, output)
            _pause(input_func)
            continue
        if choice == "2":
            _emit(output, "")
            _emit(output, render_project_requirements(project, ctx=ctx))
            _pause(input_func)
            continue
        if choice == "3":
            _emit(output, "")
            _emit(output, render_project_submission_check(project, session.rendu_dir, ctx=ctx))
            _pause(input_func)
            continue
        if choice == "4":
            _start_project_session(repo, session, project, output)
            run_correction_from_menu(repo, session, output)
            _pause(input_func)
            continue
        _emit(output, "Invalid choice.")


def _vog_name(session: Session, input_func, output=print) -> str:
    default = default_repo_name(session.load_if_exists())
    text = _ask(input_func, f"Repository name (blank for {default}): ")
    return text or default


def show_vogsphere(repo: Repository, session: Session, input_func=input, output=print) -> None:
    ctx = _ctx(output)
    while True:
        default = default_repo_name(session.load_if_exists())
        _emit(output, "")
        _emit(output, render_separator("Vogsphere", ctx=ctx))
        _emit(output, "")
        _emit(output, "Local educational simulation.")
        _emit(output, "No network, SSH, Kerberos, or real 42 server is used.")
        _emit(output, "")
        _emit(output, f"Repository    : {default}")
        _emit(output, f"Workspace     : {session.rendu_dir.relative_to(repo.root)}")
        _emit(output, "Remote store  : workspace/vogsphere")
        _emit(output, "")
        _emit(output, "  1  Init repository")
        _emit(output, "  2  Status")
        _emit(output, "  3  Commit")
        _emit(output, "  4  Log")
        _emit(output, "  5  Push")
        _emit(output, "  6  Submit")
        _emit(output, "  7  History")
        _emit(output, "  0  Back")
        _emit(output, "")
        choice = _choice(input_func, 7)
        if choice == "0":
            return
        if choice == "1":
            name = _vog_name(session, input_func, output)
            code, text = init_repo(repo.root, name, ctx=ctx)
            _emit(output, text)
            _pause(input_func)
            continue
        if choice == "2":
            name = _vog_name(session, input_func, output)
            _emit(output, render_status(repo.root, name, ctx=ctx))
            _pause(input_func)
            continue
        if choice == "3":
            name = _vog_name(session, input_func, output)
            message = _ask(input_func, "Commit message: ")
            if not message:
                message = "snapshot"
            code, text = commit_repo(repo.root, name, message=message, ctx=ctx)
            _emit(output, text)
            _pause(input_func)
            continue
        if choice == "4":
            name = _vog_name(session, input_func, output)
            code, text = log_lines(repo.root, name, ctx=ctx)
            _emit(output, text)
            _pause(input_func)
            continue
        if choice == "5":
            name = _vog_name(session, input_func, output)
            code, text = push_repo(repo.root, name, ctx=ctx)
            _emit(output, text)
            _pause(input_func)
            continue
        if choice == "6":
            name = _vog_name(session, input_func, output)
            code, text = submit_repo(repo.root, name, ctx=ctx)
            _emit(output, text)
            _pause(input_func)
            continue
        if choice == "7":
            name = _vog_name(session, input_func, output)
            code, text = history_lines(repo.root, name, ctx=ctx)
            _emit(output, text)
            _pause(input_func)
            continue
        _emit(output, "Invalid choice.")


def browse_exercises(repo: Repository, session: Session, input_func=input, output=print) -> None:
    ctx = _ctx(output)
    while True:
        _emit(output, "")
        _emit(output, render_separator("Browse Exercises", ctx=ctx))
        _emit(output, "")
        _emit(output, "  1  By Piscine module")
        _emit(output, "  2  By Exam group")
        _emit(output, "  3  Search by name")
        _emit(output, "  4  Filter by type")
        _emit(output, "  0  Back")
        _emit(output, "")
        choice = _ask(input_func)
        if choice == "1":
            _browse_piscine_module(repo, session, input_func, output)
        elif choice == "2":
            _browse_exam_group(repo, session, input_func, output)
        elif choice == "3":
            _browse_search(repo, session, input_func, output)
        elif choice == "4":
            _browse_type(repo, session, input_func, output)
        elif choice == "0":
            return
        else:
            _emit(output, "Invalid choice.")


def _subject_items(repo: Repository, subject_ids: list[str] | None = None) -> list[tuple[str, str]]:
    subjects = repo.subjects()
    ids = subject_ids if subject_ids is not None else sorted(subjects)
    out = []
    for subject_id in ids:
        entry = subjects.get(subject_id)
        if not entry:
            continue
        meta = entry["meta"]
        detail = _subject_context_detail(repo, subject_id, meta)
        out.append((subject_id, detail))
    return out


def _subject_context_detail(repo: Repository, subject_id: str, meta: dict) -> str:
    origin = str(meta.get("origin", "unknown"))
    if origin.startswith("piscine"):
        for pool_id, entry in repo.pools().items():
            pool = entry["pool"]
            if pool.get("kind") == "curriculum" and pool_id.startswith(origin):
                info = None
                for module in pool.get("modules", []) or []:
                    subjects = [str(sid) for sid in module.get("subjects", []) or []]
                    if subject_id in subjects:
                        index = subjects.index(subject_id)
                        info = f"Piscine / {module_label(module.get('id'))} / {exercise_label(index)}"
                        break
                if info:
                    return info
        level = meta.get("level")
        return f"Piscine / {module_label(meta.get('module'))} / {exercise_label(level)}"
    if origin in {"handwritten_v5", "classic_v1", "rank02_v2", "revanced_v3", "1337_2025_v4"} or "exam" in str(meta.get("module", "")):
        return f"Exam / {origin} / level {meta.get('level', 'unknown')}"
    return f"{origin} / {meta.get('module', 'unknown')}"


def _browse_piscine_module(repo: Repository, session: Session, input_func, output=print) -> None:
    curricula = [
        (pool_id, entry["pool"])
        for pool_id, entry in sorted(repo.pools().items())
        if entry["pool"].get("kind") == "curriculum" and pool_id.startswith("piscine")
    ]
    pool_id = None
    if len(curricula) == 1:
        pool_id = curricula[0][0]
    else:
        choice = _select_from_list(
            "By Piscine Module",
            [(pid, f"{pool_display_name(pid, pool)} / {len(pool.get('modules', []) or [])} modules") for pid, pool in curricula],
            input_func,
            output,
        )
        pool_id = choice
    if not pool_id:
        return
    index = choose_curriculum_module_exercise(repo, pool_id, input_func, output)
    if index is None:
        return
    pool = repo.get_pool(pool_id)
    sequence = curriculum_sequence(pool)
    item = sequence[index]
    session.start(
        repo,
        pool_id=pool_id,
        kind="piscine",
        selected=sequence,
        current_index=index,
        selection_reason="selected from exercise browser",
    )
    _emit(output, f"Selected {module_label(item.get('module'))}/{item.get('exercise_id')} {item.get('subject_id')}")
    _pause(input_func)


def _browse_exam_group(repo: Repository, session: Session, input_func, output=print) -> None:
    groups: dict[str, list[tuple[str, dict]]] = {}
    for pool_id, entry in sorted(repo.pools().items()):
        pool = entry["pool"]
        if pool.get("kind") == "exam":
            groups.setdefault(_exam_group(pool_id, pool), []).append((pool_id, pool))
    group = _select_from_list("By Exam Group", [(name, f"{len(items)} pools") for name, items in sorted(groups.items())], input_func, output)
    if not group:
        return
    pool_id = _select_from_list(
        group,
        [(pid, f"{exam_display_name(pid, pool)} / {sum(len(level.get('assignments', []) or []) for level in pool.get('levels', []) or [])} exercises") for pid, pool in groups[group]],
        input_func,
        output,
    )
    if not pool_id:
        return
    pool = repo.get_pool(pool_id)
    rows = []
    for level in pool.get("levels", []) or []:
        for sid in level.get("assignments", []) or []:
            rows.append((str(sid), f"Exam / {exam_display_name(pool_id, pool)} / Level {level.get('level')}"))
    _start_from_items(repo, session, exam_display_name(pool_id, pool), rows, input_func, output)


def _browse_type(repo: Repository, session: Session, input_func, output=print) -> None:
    types = sorted({str(entry["meta"].get("type", "unknown")) for entry in repo.subjects().values()})
    subject_type = _select_from_list("Filter by Type", [(item, "") for item in types], input_func, output)
    if not subject_type:
        return
    matches = [
        (subject_id, _subject_context_detail(repo, subject_id, entry["meta"]))
        for subject_id, entry in sorted(repo.subjects().items())
        if str(entry["meta"].get("type", "unknown")) == subject_type
    ]
    _start_from_items(repo, session, f"Type {subject_type}", matches, input_func, output)


def _browse_search(repo: Repository, session: Session, input_func, output=print) -> None:
    query = _ask(input_func, "Search (blank to cancel): ").lower()
    if not query:
        return
    matches = []
    for subject_id, entry in sorted(repo.subjects().items()):
        title = str(entry["meta"].get("title", ""))
        if query in subject_id.lower() or query in title.lower():
            matches.append((subject_id, _subject_context_detail(repo, subject_id, entry["meta"])))
    _start_from_items(repo, session, "Search Results", matches, input_func, output)


def _browse_module(repo: Repository, session: Session, input_func, output=print) -> None:
    modules = sorted({str(entry["meta"].get("module", "unknown")) for entry in repo.subjects().values()})
    module = _select_from_list("Modules", [(item, "") for item in modules], input_func, output)
    if not module:
        return
    matches = [
        (subject_id, entry["meta"].get("title", ""))
        for subject_id, entry in sorted(repo.subjects().items())
        if str(entry["meta"].get("module", "unknown")) == module
    ]
    _start_from_items(repo, session, f"Module {module}", matches, input_func, output)


def _browse_pool(repo: Repository, session: Session, input_func, output=print) -> None:
    pools = [(pool_id, entry["pool"].get("kind", "")) for pool_id, entry in sorted(repo.pools().items())]
    pool_id = _select_from_list("Pools", pools, input_func, output)
    if not pool_id:
        return
    pool = repo.get_pool(pool_id)
    _start_from_items(repo, session, f"Pool {pool_id}", _subject_items(repo, repo.pool_subject_ids(pool)), input_func, output)


def _browse_recent(repo: Repository, session: Session, input_func, output=print) -> None:
    data = load_progress(repo.root)
    seen = []
    for item in reversed(data.get("attempt_log", [])):
        subject_id = item.get("subject_id")
        if subject_id and subject_id not in seen:
            seen.append(subject_id)
        if len(seen) >= 20:
            break
    current_state = session.load_if_exists()
    current = None
    if current_state:
        selected = current_state.get("selected", [])
        index = int(current_state.get("current_index", 0))
        if selected and 0 <= index < len(selected):
            current = selected[index].get("subject_id")
    ids = ([current] if current else []) + [sid for sid in seen if sid != current]
    _start_from_items(repo, session, "Current / Recent", _subject_items(repo, ids), input_func, output)


def _start_from_items(
    repo: Repository,
    session: Session,
    title: str,
    items: list[tuple[str, str]],
    input_func,
    output=print,
) -> None:
    subject_id = _select_from_list(title, items, input_func, output)
    if subject_id:
        session.set_current_subject(repo, subject_id)
        _emit(output, f"Started exercise: {subject_id}")
        _pause(input_func)


def show_current(repo: Repository, session: Session, output=print) -> None:
    _emit(output, format_current(repo, session.root, session.load_if_exists(), _ctx(output)))


def show_exam_terminal(repo: Repository, session: Session, input_func=input, output=print) -> None:
    ctx = _ctx(output)
    while True:
        state = session.load_if_exists()
        if not state or state.get("mode") != "exam":
            _emit(output, "No active Exam session.")
            _pause(input_func)
            return
        _emit(output, "")
        _emit(output, render_exam_screen(repo, session.root, state, ctx=ctx))
        _emit(output, "")
        choice = _choice(input_func, 5)
        if choice == "0":
            return
        if choice == "1":
            _emit(output, "")
            _emit(output, repo.subject_text(session.current_subject_id()))
            _pause(input_func)
            continue
        if choice == "2":
            run_correction_from_menu(repo, session, output)
            _pause(input_func)
            continue
        if choice == "3":
            show_trace(repo, session, output)
            _pause(input_func)
            continue
        if choice == "4":
            show_progress(repo, session, output)
            _pause(input_func)
            continue
        if choice == "5":
            _emit(output, render_exam_rules(ctx=ctx))
            _pause(input_func)
            continue
        _emit(output, "Invalid choice.")


def _attempts_for_trace(repo: Repository, trace: dict) -> int | None:
    subject_id = trace.get("subject_id")
    if not subject_id:
        return None
    data = load_progress(repo.root)
    value = data.get("subjects", {}).get(subject_id, {}).get("attempts")
    return int(value) if value is not None else None


def run_correction_from_menu(repo: Repository, session: Session, output=print) -> int:
    state = session.load_if_exists()
    if not state:
        _emit(output, "No active session. Start a Piscine or Exam first.")
        return 1
    label = correction_label(state)
    _emit(output, f"Running {label}...")
    trace = evaluate_subject(repo, session)
    paths = write_trace_bundle(session.trace_dir, trace)
    record_attempt(repo, session, trace, paths["latest"])
    attempts = _attempts_for_trace(repo, trace)
    outcome = None
    if trace["status"] == "OK":
        advanced = session.advance_after_success(repo)
        if label == "Grademe":
            if advanced:
                next_state = session.load_if_exists()
                next_info = exam_context(repo, next_state)
                outcome = f"Level unlocked: {next_info['level']} / {next_info['level_count']}"
            else:
                outcome = "Exam complete."
        elif label == "Project Moulinette":
            outcome = "Project correction complete."
        else:
            outcome = f"Next subject: {session.current_subject_id()}" if advanced else "Session complete."
    elif label == "Grademe":
        outcome = "Stay on current level."
    elif label == "Moulinette":
        outcome = "Stay on current subject."
    elif label == "Project Moulinette":
        outcome = "Stay on current project."
    _emit(
        output,
        render_correction_result(
            root=repo.root,
            state=state,
            trace=trace,
            trace_file=paths["latest"],
            attempts=attempts,
            outcome=outcome,
            repo=repo,
            ctx=_ctx(output),
        ),
    )
    return 0 if trace["status"] == "OK" else 1


def run_grademe_from_menu(repo: Repository, session: Session, output=print) -> int:
    return run_correction_from_menu(repo, session, output)


def show_trace(repo: Repository, session: Session, output=print) -> None:
    del repo
    path = latest_trace(session.trace_dir)
    _emit(output, "")
    _emit(output, render_separator(f"{correction_label(session.load_if_exists())} Trace", ctx=_ctx(output)))
    if path is None:
        _emit(output, f"No trace found in {session.trace_dir}")
        return
    _emit(output, summarize_trace(read_trace(path)))
    _emit(output, f"trace: {path}")


def show_progress(repo: Repository, session: Session, output=print) -> None:
    _emit(output, summarize_progress(repo, session.root, session.load_if_exists(), _ctx(output)))


def show_history(repo: Repository, session: Session, output=print) -> None:
    _emit(output, summarize_history(repo, session.root, session.load_if_exists(), ctx=_ctx(output)))


def _validate(repo: Repository, output=print) -> int:
    errors = repo.validate()
    if errors:
        for err in errors:
            _emit(output, f"KO: {err}")
        return 1
    _emit(output, "OK: repository is valid")
    return 0
