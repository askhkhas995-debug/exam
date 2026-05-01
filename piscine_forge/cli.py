from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .correction_source import (
    SourceError,
    materialized_source,
    render_source_error,
    render_source_lines,
    resolve_source,
    trace_source,
)
from .correction_ux import correction_label, is_curriculum, is_exam, render_correction_result
from .curriculum import current_curriculum_context, exam_context
from .doctor import render_doctor
from .evaluators import evaluate_subject
from .exam_ui import render_exam_rules, render_exam_screen, render_exam_started, render_exam_status
from .loader import Repository, find_repo_root
from .moulinette_summary import build_module_summary, render_module_summary, write_module_summary_trace
from .picker import curriculum_sequence, pick_from_pool
from .progress import (
    format_current,
    init_curriculum_progress,
    init_exam_progress,
    load_progress,
    record_attempt,
    summarize_history,
    summarize_module_progress,
    summarize_progress,
)
from .projects import (
    current_project,
    find_piscine_project,
    render_project_list,
    render_project_requirements,
    render_project_submission_check,
    render_project_references,
    render_project_subject_result,
)
from .reset import ResetCancelled, reset_all, reset_progress, reset_session, reset_traces
from .session import Session
from .trace import latest_trace, read_trace, summarize_trace, write_trace_bundle
from .ui import render_context
from .vogsphere import (
    commit_repo,
    default_repo_name,
    history_lines,
    init_repo,
    log_lines,
    push_repo,
    render_status as render_vog_status,
    submit_repo,
)


START_ALIASES = {
    "piscine42": "piscine42_default",
}


def _add_correction_parser(sub, name: str, help_text: str, *, add_source: bool = False) -> None:
    correction_p = sub.add_parser(name, help=help_text)
    correction_p.add_argument("subject_arg", nargs="?")
    correction_p.add_argument("--subject", default=None)
    if add_source:
        correction_p.add_argument("--source", choices=["rendu", "vog"], default="rendu", help="correction source")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pforge",
        description="PiscineForge: terminal-first 42 Piscine and exam practice.",
        epilog=(
            "Run `pforge menu` for the interactive launcher. Student files go in "
            "workspace/rendu/. Piscine uses Moulinette; Exam uses Grademe; "
            "Vogsphere is local educational storage only."
        ),
    )
    parser.add_argument("--version", action="version", version=f"PiscineForge {__version__}")
    sub = parser.add_subparsers(dest="cmd", metavar="command")

    sub.add_parser("validate", help="validate repository subjects, pools, and correction metadata")
    sub.add_parser("doctor", help="show install, dependency, repository, and workspace diagnostics")
    sub.add_parser("version", help="print PiscineForge version")

    list_p = sub.add_parser("list", help="list available subjects or pools")
    list_p.add_argument("what", choices=["subjects", "pools"])

    start_p = sub.add_parser("start", help="start a curriculum path")
    start_p.add_argument("path", choices=["piscine42"])
    start_p.add_argument("--seed", type=int, default=None)
    start_p.add_argument("--subject", default=None)

    exam_p = sub.add_parser(
        "exam",
        help="start an exam pool or show exam status/rules",
        description=(
            "Start an exam pool, or use `pforge exam status`, "
            "`pforge exam rules`, or `pforge exam current` for the active exam."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    exam_p.add_argument("pool", nargs="?", metavar="{status,rules,current,POOL}")
    exam_p.add_argument("--seed", type=int, default=None, help="select deterministic exam subjects")
    exam_p.add_argument("--subject", default=None, help="start the exam on a specific subject when available")

    subject_p = sub.add_parser("subject", help="read or change the current subject")
    subject_sub = subject_p.add_subparsers(dest="subject_cmd")
    subject_sub.add_parser("current")
    set_p = subject_sub.add_parser("set")
    set_p.add_argument("subject_id")

    _add_correction_parser(sub, "correct", "run the active session correction", add_source=True)
    moulinette_p = sub.add_parser(
        "moulinette",
        help="run Piscine-style Moulinette correction or show a module summary",
        description=(
            "Run Piscine-style correction for the active/current subject.\n"
            "Default source is workspace/rendu/. Use `--source vog` to correct "
            "the latest local submitted Vogsphere snapshot.\n"
            "Use `pforge moulinette summary` to show an optional module summary "
            "from current progress and traces; it does not re-run the whole module."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    moulinette_p.add_argument(
        "target",
        nargs="?",
        metavar="{summary|SUBJECT}",
        help="subject id to correct, or `summary` to show the current module summary",
    )
    moulinette_p.add_argument("--subject", default=None)
    moulinette_p.add_argument("--write-trace", action="store_true", help="write a module summary trace for `pforge moulinette summary`")
    moulinette_p.add_argument("--source", choices=["rendu", "vog"], default="rendu", help="correction source")
    _add_correction_parser(sub, "grademe", "grade the current or specified subject")

    module_p = sub.add_parser("module", help="show current Piscine module structure and progress")
    module_sub = module_p.add_subparsers(dest="module_cmd")
    module_sub.add_parser("list", help="list modules in the active Piscine")
    module_sub.add_parser("current", help="show the current module and exercise")
    module_sub.add_parser("progress", help="show current module progress")

    trace_p = sub.add_parser("trace", help="show latest trace or traceback")
    trace_p.add_argument("--json", action="store_true")

    sub.add_parser("menu", help="open the interactive terminal launcher")
    sub.add_parser("interface", help="alias for menu")
    sub.add_parser("projects", help="list existing Piscine projects")
    sub.add_parser("current", help="show the active subject summary")

    project_p = sub.add_parser(
        "project",
        help="inspect existing Piscine project requirements and submissions",
        description=(
            "Inspect local project metadata and preflight-check workspace/rendu/ "
            "or `--source vog`. Some virtual projects may report metadata incomplete."
        ),
    )
    project_sub = project_p.add_subparsers(dest="project_cmd")
    project_sub.add_parser("list", help="list existing Piscine projects")
    project_sub.add_parser("current", help="show the active project")
    requirements_p = project_sub.add_parser("requirements", help="show project submission requirements")
    requirements_p.add_argument("project", nargs="?", metavar="project")
    check_p = project_sub.add_parser("check", help="preflight-check project files in workspace/rendu")
    check_p.add_argument("project", nargs="?", metavar="project")
    check_p.add_argument("--source", choices=["rendu", "vog"], default="rendu", help="submission source")
    references_p = project_sub.add_parser("references", help="show legacy reference repository catalog")
    references_p.add_argument("project", nargs="?", metavar="project", help="filter by specific project")
    subject_p = project_sub.add_parser("subject", help="show or copy local legacy subject pdf/text")
    subject_p.add_argument("project", nargs="?", metavar="project")
    subject_p.add_argument("--copy-to", metavar="path", help="copy the local subject to this path")

    vog_p = sub.add_parser(
        "vog",
        help="local educational Vogsphere simulation",
        description=(
            "Manage local educational Vogsphere snapshots. External services, "
            "SSH, Kerberos, and real 42/Vogsphere services are not used. Submitted "
            "snapshots are optional sources only when a command uses `--source vog`."
        ),
    )
    vog_sub = vog_p.add_subparsers(dest="vog_cmd")
    vog_help = {
        "init": "initialize a local educational Vogsphere repo",
        "status": "show local Vogsphere repo status",
        "log": "show local Vogsphere commits",
        "push": "mark the latest commit as pushed locally",
        "submit": "mark the latest pushed commit as submitted locally",
        "history": "show local Vogsphere action history",
    }
    for name, help_text in vog_help.items():
        child = vog_sub.add_parser(name, help=help_text)
        child.add_argument("name", nargs="?", metavar="name")
    commit_p = vog_sub.add_parser("commit", help="snapshot workspace/rendu into local Vogsphere")
    commit_p.add_argument("name", nargs="?", metavar="name")
    commit_p.add_argument("-m", "--message", required=True, help="commit message")

    reset_p = sub.add_parser("reset", help="safely clear generated workspace state")
    reset_sub = reset_p.add_subparsers(dest="reset_cmd")
    for name in ["session", "progress", "traces", "all"]:
        child = reset_sub.add_parser(name)
        child.add_argument("--yes", action="store_true")

    history_p = sub.add_parser("history", help="show progress history")
    history_p.add_argument("view", nargs="?", choices=["failed", "completed", "attempts"])

    sub.add_parser("status", help="show progress and time status")
    sub.add_parser("finish", help="finish the active session without deleting student work")
    return parser


def _repo_session() -> tuple[Repository, Session]:
    root = find_repo_root(Path.cwd())
    repo = Repository(root)
    session = Session(root)
    session.ensure()
    return repo, session


def _print_selection(state: dict) -> None:
    print(f"session: {state['kind']} {state['pool_id']}")
    if state.get("seed") is not None:
        print(f"seed: {state['seed']}")
    repo, _session = _repo_session()
    if state.get("mode") == "exam":
        ctx = exam_context(repo, state)
        print(f"exam: {ctx['exam']} ({ctx['pool_id']})")
        print(f"level: {ctx['level']} / {ctx['level_count']}")
        print(f"exercise: {ctx['subject_id']}")
        print(f"correction: Grademe")
        for index, item in enumerate(state.get("selected", [])):
            marker = ">" if index == state.get("current_index", 0) else " "
            print(f"{marker} {item.get('level', index)}: {item['subject_id']}")
        print("subject: workspace/subject/subject.en.txt")
        print("rendu: workspace/rendu/")
        return
    if state.get("mode") == "curriculum":
        ctx = current_curriculum_context(repo, state)
        print(f"pool: {ctx['pool_id']}")
        print(f"module: {ctx['module']} ({ctx['module_id']})")
        print(f"exercise: {ctx['exercise_id']}")
        print(f"subject: {ctx['subject_id']}")
        print(f"reason: {ctx['reason']}")
        print(f"next: {ctx['next_subject_id']}")
        print("subject file: workspace/subject/subject.en.txt")
        print("rendu: workspace/rendu/")
        return
    if len(state["selected"]) > 30:
        current = state["selected"][state["current_index"]]
        next_item = state["selected"][state["current_index"] + 1] if state["current_index"] + 1 < len(state["selected"]) else None
        print(f"selected: {len(state['selected'])} exercises")
        print(f"current: {current.get('module', current.get('level', state['current_index']))}: {current['subject_id']}")
        print(f"next: {next_item['subject_id'] if next_item else 'none'}")
        print("subject: workspace/subject/subject.en.txt")
        print("rendu: workspace/rendu/")
        return
    for index, item in enumerate(state["selected"]):
        marker = ">" if index == state["current_index"] else " "
        level = item.get("level", item.get("module", index))
        print(f"{marker} {level}: {item['subject_id']}")
    print("subject: workspace/subject/subject.en.txt")
    print("rendu: workspace/rendu/")


def _pool_duration_seconds(pool: dict) -> int | None:
    minutes = pool.get("duration_minutes")
    return int(minutes) * 60 if minutes is not None else None


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _current_subject_from_state(state: dict) -> str | None:
    selected = state.get("selected") or []
    index = int(state.get("current_index", 0))
    if selected and 0 <= index < len(selected):
        return selected[index].get("subject_id")
    return None


def _attempts_for_trace(repo: Repository, trace: dict) -> int | None:
    subject_id = trace.get("subject_id")
    if not subject_id:
        return None
    data = load_progress(repo.root)
    value = data.get("subjects", {}).get(subject_id, {}).get("attempts")
    return int(value) if value is not None else None


def _no_active_correction_message() -> str:
    return "No active session. Start a Piscine with `pforge start piscine42` or an Exam with `pforge exam <pool>` first."


def _run_correction_command(repo: Repository, session: Session, args) -> int:
    target = getattr(args, "target", None)
    if args.cmd == "moulinette" and target == "summary" and not args.subject:
        if getattr(args, "source", "rendu") != "rendu":
            print("Moulinette summary does not use a correction source.")
            return 1
        return _run_moulinette_summary_command(repo, session, write_summary_trace=bool(getattr(args, "write_trace", False)))

    subject = args.subject or target or getattr(args, "subject_arg", None)
    state = session.load_if_exists()
    manual_subject = bool(subject and not state)
    if args.cmd in {"correct", "moulinette"} and not state:
        print(_no_active_correction_message())
        return 1
    if args.cmd == "moulinette" and is_exam(state):
        print("Exam sessions use Grademe. Run `pforge grademe` or `pforge correct`.")
        return 1
    source_name = getattr(args, "source", "rendu")
    if source_name != "rendu" and is_exam(state):
        print("Exam/Grademe correction uses workspace/rendu. Vogsphere is not an Exam source.")
        return 1
    if args.cmd == "grademe" and is_curriculum(state):
        print("Active Piscine sessions use Moulinette; running Moulinette.")
    if subject:
        session.set_current_subject(repo, subject)
    elif not session.state_path.exists():
        print("No active session. Run `pforge start ...`, `pforge exam ...`, or pass --subject.")
        return 1

    state = session.load_if_exists()
    label = correction_label(state)
    run_label = "manual correction" if manual_subject else label
    if label == "Grademe":
        print(f"Running {run_label}...")
        trace = evaluate_subject(repo, session)
    else:
        source = resolve_source(repo.root, source_name, preferred_name=session.current_subject_id())
        if isinstance(source, SourceError):
            print(render_source_error(source, ctx=render_context(sys.stdout)))
            return 1
        print(f"Running {run_label}...")
        for line in render_source_lines(source, ctx=render_context(sys.stdout)):
            print(line)
        try:
            with materialized_source(source) as source_dir:
                trace = evaluate_subject(repo, session, source_dir=source_dir)
        except ValueError as exc:
            print(render_source_error(SourceError(source=source.source, reason=str(exc)), ctx=render_context(sys.stdout)))
            return 1
        trace["correction_source"] = trace_source(source)
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
        elif label == "Moulinette":
            outcome = f"Next subject: {session.current_subject_id()}" if advanced else "Session complete."
        elif label == "Project Moulinette":
            outcome = "Project correction complete."
        else:
            outcome = "Session complete."
    elif label == "Grademe":
        outcome = "Stay on current level."
    elif label == "Moulinette":
        outcome = "Stay on current subject."
    elif label == "Project Moulinette":
        outcome = "Stay on current project."

    print(
        render_correction_result(
            root=repo.root,
            state=state,
            trace=trace,
            trace_file=paths["latest"],
            attempts=attempts,
            outcome=outcome,
            repo=repo,
            ctx=render_context(sys.stdout),
        )
    )
    return 0 if trace["status"] == "OK" else 1


def _run_moulinette_summary_command(repo: Repository, session: Session, *, write_summary_trace: bool = False) -> int:
    state = session.load_if_exists()
    if not state:
        print(_no_active_correction_message())
        return 1
    if not is_curriculum(state):
        print("Moulinette summary is only available for Piscine/curriculum sessions.")
        return 1
    trace_file = None
    if write_summary_trace:
        summary = build_module_summary(repo, repo.root, state)
        trace_file = write_module_summary_trace(repo.root, summary)
    print(render_module_summary(repo, repo.root, state, trace_file=trace_file, ctx=render_context(sys.stdout)))
    return 0


def _project_from_arg_or_session(repo: Repository, session: Session, project_id: str | None) -> dict | None:
    if project_id:
        return find_piscine_project(repo, project_id)
    return current_project(repo, session.load_if_exists())


def main(argv=None) -> int:
    raw_argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    if not raw_argv:
        if _is_interactive():
            repo, _session = _repo_session()
            from . import interface

            return interface.run_menu(repo)
        parser.print_help()
        return 0
    args = parser.parse_args(raw_argv)
    repo, session = _repo_session()

    if args.cmd == "validate":
        errors = repo.validate()
        if errors:
            for err in errors:
                print(f"KO: {err}")
            return 1
        print("OK: repository is valid")
        return 0

    if args.cmd == "doctor":
        text, code = render_doctor(repo, session, ctx=render_context(sys.stdout))
        print(text)
        return code

    if args.cmd == "version":
        print(f"PiscineForge {__version__}")
        return 0

    if args.cmd == "list":
        if args.what == "subjects":
            for sid, entry in sorted(repo.subjects().items()):
                meta = entry["meta"]
                suffix = " virtual" if entry.get("virtual") else ""
                print(f"{sid}\t{meta.get('type')}\t{meta.get('origin')}\t{meta.get('module')}{suffix}")
        else:
            for pid, entry in sorted(repo.pools().items()):
                pool = entry["pool"]
                print(f"{pid}\t{pool.get('kind')}\t{pool.get('version', '')}")
        return 0

    if args.cmd == "start":
        pool_id = START_ALIASES[args.path]
        pool = repo.get_pool(pool_id)
        selected = curriculum_sequence(pool)
        state = session.start(
            repo,
            pool_id=pool_id,
            kind=args.path,
            selected=selected,
            seed=args.seed,
            subject_id=args.subject,
            duration_seconds=_pool_duration_seconds(pool),
            selection_reason="selected by command" if args.subject else "first exercise in module",
        )
        init_curriculum_progress(repo, repo.root, pool_id, _current_subject_from_state(state) or "", state)
        _print_selection(state)
        return 0

    if args.cmd == "exam":
        if args.pool in {"status", "rules", "current"}:
            state = session.load_if_exists()
            if not state or not is_exam(state):
                print("No active Exam session. Start with `pforge exam <pool>` first.")
                return 1
            ctx = render_context(sys.stdout)
            if args.pool == "rules":
                print(render_exam_rules(ctx=ctx))
                return 0
            if args.pool == "current":
                print(render_exam_screen(repo, repo.root, state, ctx=ctx))
                return 0
            print(render_exam_status(repo, repo.root, load_progress(repo.root), state, ctx=ctx))
            return 0
        if not args.pool:
            parser.print_help()
            return 2
        pool = repo.get_pool(args.pool)
        selected = pick_from_pool(pool, seed=args.seed)
        state = session.start(
            repo,
            pool_id=args.pool,
            kind="exam",
            selected=selected,
            seed=args.seed,
            subject_id=args.subject,
            duration_seconds=_pool_duration_seconds(pool),
        )
        init_exam_progress(repo.root, args.pool, args.seed, state["selected"], state)
        print(render_exam_started(repo, state, ctx=render_context(sys.stdout)))
        return 0

    if args.cmd == "subject":
        if args.subject_cmd == "current":
            sid = session.current_subject_id()
            print(repo.subject_text(sid))
            return 0
        if args.subject_cmd == "set":
            session.set_current_subject(repo, args.subject_id)
            print(f"current subject: {args.subject_id}")
            return 0
        parser.print_help()
        return 2

    if args.cmd == "module":
        state = session.load_if_exists()
        if not state or not is_curriculum(state):
            print("No active Piscine session. Start with `pforge start piscine42` first.")
            return 1
        if args.module_cmd == "list":
            pool = repo.get_pool(state["pool_id"])
            for module in pool.get("modules", []) or []:
                subjects = module.get("subjects", []) or []
                from .curriculum import module_label

                print(f"{module_label(module.get('id'))}\t{module.get('id')}\t{len(subjects)} exercises")
            return 0
        if args.module_cmd == "current":
            print(format_current(repo, repo.root, state, render_context(sys.stdout)))
            return 0
        if args.module_cmd == "progress":
            print(summarize_module_progress(repo, repo.root, state, render_context(sys.stdout)))
            return 0
        parser.print_help()
        return 2

    if args.cmd in {"correct", "moulinette", "grademe"}:
        return _run_correction_command(repo, session, args)

    if args.cmd == "trace":
        path = session.trace_dir / ("latest.json" if args.json else "traceback.txt")
        if not path.exists():
            trace_json = latest_trace(session.trace_dir)
            if trace_json is None:
                print("No trace found")
                return 1
            if args.json:
                path = trace_json
        if args.json:
            print(path.read_text(encoding="utf-8"), end="")
        elif path.exists():
            print(path.read_text(encoding="utf-8"), end="")
        else:
            trace_json = latest_trace(session.trace_dir)
            if trace_json is None:
                print("No trace found")
                return 1
            print(summarize_trace(read_trace(trace_json)))
        return 0

    if args.cmd in {"menu", "interface"}:
        from . import interface

        return interface.run_menu(repo)

    if args.cmd == "projects":
        print(render_project_list(repo, ctx=render_context(sys.stdout)))
        return 0

    if args.cmd == "project":
        ctx = render_context(sys.stdout)
        if args.project_cmd == "list":
            print(render_project_list(repo, ctx=ctx))
            return 0
        if args.project_cmd == "current":
            project = current_project(repo, session.load_if_exists())
            if not project:
                print("No active project. Use `pforge project list` or `pforge project requirements <project>`.")
                return 1
            print(f"Project: {project['name']} ({project['id']})")
            print("Correction: Project Moulinette")
            print("Rendu: workspace/rendu/")
            return 0
        if args.project_cmd in {"requirements", "check"}:
            project = _project_from_arg_or_session(repo, session, args.project)
            if not project:
                print("Unknown or missing project. Use `pforge project list`.")
                return 1
            if args.project_cmd == "requirements":
                print(render_project_requirements(project, repo, ctx=ctx))
                return 0
            source = resolve_source(repo.root, args.source, preferred_name=str(project["id"]))
            if isinstance(source, SourceError):
                print(render_source_error(source, ctx=ctx))
                return 1
            try:
                with materialized_source(source) as source_dir:
                    print(render_project_submission_check(project, source_dir, source=source, ctx=ctx))
            except ValueError as exc:
                print(render_source_error(SourceError(source=source.source, reason=str(exc)), ctx=ctx))
                return 1
            return 0
        if args.project_cmd == "references":
            print(render_project_references(repo, getattr(args, "project", None), ctx=ctx))
            return 0
        if args.project_cmd == "subject":
            project = _project_from_arg_or_session(repo, session, args.project)
            if not project:
                print("Unknown or missing project. Use `pforge project list`.")
                return 1
            code, text = render_project_subject_result(repo, str(project["id"]), getattr(args, "copy_to", None), ctx=ctx)
            print(text)
            return code
        parser.print_help()
        return 2

    if args.cmd == "vog":
        default_name = default_repo_name(session.load_if_exists())
        name = getattr(args, "name", None) or default_name
        ctx = render_context(sys.stdout)
        if args.vog_cmd == "init":
            code, text = init_repo(repo.root, name, ctx=ctx)
        elif args.vog_cmd == "status":
            code, text = 0, render_vog_status(repo.root, name, ctx=ctx)
        elif args.vog_cmd == "commit":
            code, text = commit_repo(repo.root, name, message=args.message, ctx=ctx)
        elif args.vog_cmd == "log":
            code, text = log_lines(repo.root, name, ctx=ctx)
        elif args.vog_cmd == "push":
            code, text = push_repo(repo.root, name, ctx=ctx)
        elif args.vog_cmd == "submit":
            code, text = submit_repo(repo.root, name, ctx=ctx)
        elif args.vog_cmd == "history":
            code, text = history_lines(repo.root, name, ctx=ctx)
        else:
            parser.print_help()
            return 2
        print(text)
        return code

    if args.cmd == "current":
        print(format_current(repo, repo.root, session.load_if_exists(), render_context(sys.stdout)))
        return 0

    if args.cmd == "reset":
        if not args.reset_cmd:
            parser.print_help()
            return 2
        try:
            if args.reset_cmd == "session":
                deleted = reset_session(session, yes=args.yes)
            elif args.reset_cmd == "progress":
                deleted = reset_progress(session, yes=args.yes)
            elif args.reset_cmd == "traces":
                deleted = reset_traces(session, yes=args.yes)
            else:
                deleted = reset_all(session, yes=args.yes)
        except ResetCancelled as exc:
            print(exc)
            return 1
        print(f"reset {args.reset_cmd}: {len(deleted)} item(s)")
        return 0

    if args.cmd == "history":
        print(summarize_history(repo, repo.root, session.load_if_exists(), args.view or "all", render_context(sys.stdout)))
        return 0

    if args.cmd == "status":
        print(summarize_progress(repo, repo.root, session.load_if_exists(), render_context(sys.stdout)))
        return 0

    if args.cmd == "finish":
        session.finish()
        print("session finished")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
