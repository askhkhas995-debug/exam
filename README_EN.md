# PiscineForge

PiscineForge is a terminal-first 42 Piscine and Friday Exam practice simulator.
It is not official 42 software. It is a Terminal UI, not a GUI. The default
style is school-style and minimal: aligned labels, calm separators, and no
emojis by default.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Without installation, use:

```bash
python3 -m piscine_forge.cli --help
```

## Quickstart

Run:

```bash
pforge menu
pforge validate
pforge start piscine42
pforge current
pforge moulinette
```

Read subjects in `workspace/subject/` and put your files in
`workspace/rendu/`. Corrections, hidden mains, and private tests are not copied
to the student workspace.

Exam example:

```bash
pforge exam handwritten_v5 --subject first_last_char
pforge grademe
pforge exam status
```

Projects example:

```bash
pforge projects
pforge project requirements bsq
pforge project check bsq
```

Vogsphere example:

```bash
pforge vog init demo
pforge vog status demo
pforge vog commit -m "initial" demo
pforge vog push demo
pforge vog submit demo
```

## Command Map

Core:

```bash
pforge menu
pforge validate
pforge doctor
pforge current
pforge status
pforge trace
pforge history
```

Piscine:

```bash
pforge start piscine42
pforge start piscine42
pforge moulinette
pforge moulinette --source vog
pforge correct
pforge module list
pforge module current
pforge module progress
```

Exam:

```bash
pforge exam <pool>
pforge exam status
pforge exam rules
pforge grademe
```

Projects:

```bash
pforge projects
pforge project list
pforge project current
pforge project requirements <project>
pforge project check <project>
pforge project check <project> --source vog
```

Vogsphere:

```bash
pforge vog init [name]
pforge vog status [name]
pforge vog commit -m "message" [name]
pforge vog log [name]
pforge vog push [name]
pforge vog submit [name]
pforge vog history [name]
```

## Piscine: Moulinette

Start a Piscine path:

```bash
pforge start piscine42
```

Solve the active subject in `workspace/rendu/`, then run Moulinette:

```bash
pforge correct
pforge moulinette
pforge moulinette summary
```

An OK Moulinette result advances progress when another subject is selected. The
Moulinette trace contains correction details under `workspace/traces/`.
`pforge correct` is mode-aware. In a Piscine session, `pforge grademe` is kept
only as compatibility and clearly warns that the active session uses
Moulinette.

Curriculum navigation is module-aware. `pforge current`, `pforge status`, and
the terminal menu show Pool, Module, Exercise, Subject, and Next. Use
`pforge module list` and `pforge module progress` to inspect the active module
without running correction.

`pforge moulinette summary` prints an optional Moulinette-style module summary
from the current session, progress, and trace data. It is a summary layer only:
it does not re-run the whole module and does not replace the single-subject
Moulinette evaluator.
Full module correction is future work and is not implemented by this command.

## Exam: Grademe

Start an exam:

```bash
pforge exam handwritten_v5 --seed 42
```

Solve the selected exercise in `workspace/rendu/`, then run Grademe:

```bash
pforge grademe
pforge correct
```

An OK Grademe result unlocks the next level when one is available. The Grademe
trace contains correction details under `workspace/traces/`.
In an Exam session, `pforge moulinette` refuses and points you back to
`pforge grademe` or `pforge correct`.

## Projects and Local Vogsphere

`pforge projects` lists only project entries that are currently scaffolded in
the repository: Rush00, Rush01, Rush02, Sastantua, Match-N-Match, Eval Expr,
and BSQ.

Use project preflight commands to inspect the local submission contract and
check `workspace/rendu/` before full correction:

```bash
pforge project list
pforge project requirements bsq
pforge project check bsq
```

Rush and Eval Expr projects have local preflight submission contracts.
BSQ has local functional tests. Project Moulinette tests are local, reverse-engineered, reproducible trainer tests. They are not official 42 tests. See `docs/PROJECT_TESTING_POLICY.md` for details. Sastantua and Match-N-Match are still reported honestly as metadata-incomplete until detailed submission contracts are added.

For legacy subjects like BSQ, Rush, and Sastantua, PiscineForge uses local project data. Local reference PDFs and metadata live in `resources/legacy_subjects/`. External repositories and links are catalog entries only. Remote downloads are disabled.

`pforge vog` is a local educational Vogsphere simulation. It snapshots
`workspace/rendu/` into `workspace/vogsphere/repos/<name>/` and keeps local
metadata in `workspace/vogsphere/state.json`.

```bash
pforge vog status myrepo
pforge vog init myrepo
pforge vog commit -m "initial submit" myrepo
pforge vog log myrepo
pforge vog push myrepo
pforge vog submit myrepo
pforge vog history myrepo
```

This layer is local educational storage only. External services are not used;
SSH, Kerberos, real 42 servers, and `~/.ssh` are out of scope.
Default correction and project checks still inspect `workspace/rendu/`.
Moulinette and project checks can opt into the latest submitted local
Vogsphere snapshot with `--source vog`. Grademe continues to use
`workspace/rendu/`; Exam does not use Vogsphere.

## Explicit Limitations and Boundaries

- **Project Moulinette is local-only.** It is not the official 42 Moulinette.
- It does not connect to real 42 services.
- Real Vogsphere, SSH, Kerberos, and official 42 service integration are out of scope.
- Remote downloads are disabled.
- Legacy repositories were used only during one-time preparation.
- PDFs under `resources/legacy_subjects/projects/<project>/` are local reference copies only.
- Existing built-in Piscine and exam subjects remain authoritative and are not touched.
- No solutions are imported, copied, displayed, or used.
- Project support status varies by project.

## Safe Reset

```bash
pforge reset session
pforge reset progress
pforge reset traces
pforge reset all
```

`reset progress`, `reset traces`, and `reset all` ask for confirmation unless
`--yes` is passed. `reset all` keeps `workspace/rendu/` by default.

## Themes

```bash
PFORGE_THEME=official pforge menu
PFORGE_THEME=tokyo-night pforge menu
PFORGE_THEME=gruvbox pforge menu
PFORGE_THEME=plain pforge menu
```

`PFORGE_THEME=graphbox` maps to `gruvbox`. Use `NO_COLOR=1` or
`PFORGE_THEME=plain` to disable colors. Colors are only emitted when stdout is a
TTY.

PiscineForge cannot set your terminal font. Configure fonts in your terminal
app. Recommended readable fonts: JetBrains Mono, IBM Plex Mono, Hack, Fira Code,
or MesloLGS. Nerd Fonts are optional.

## Safety and Packaging Notes

PiscineForge is an educational local simulator, not a secure remote judge and
not official 42 software. The local repo may contain correction fixtures under
`resources/` and private correction metadata under `corrections/`; these files
are not copied into the student-visible `workspace/subject/`. This protects the
student workspace, but it is not secure against someone reading the repository.
A public challenge distribution would need a different packaging strategy for
private fixtures.

The Vogsphere layer is local educational simulation only. PiscineForge does not
use Kerberos, does not upload anywhere, does not modify SSH configuration, does
not connect to official 42 services, and does not provide a GUI.

Default correction reads `workspace/rendu/`. Submitted Vogsphere snapshots are
optional local sources only when `--source vog` is passed to Moulinette or
project checks. Vogsphere does not affect Grademe or Exam. Any future local
Exam Submit workflow must be separate from Vogsphere. Some virtual project
metadata may remain incomplete.

## Release Smoke Checklist

```bash
python3 -m compileall -q piscine_forge
python3 -m pytest -q
python3 -m piscine_forge.cli validate
python3 -m piscine_forge.cli menu
python3 -m piscine_forge.cli projects
python3 -m piscine_forge.cli vog status
python3 -m piscine_forge.cli exam handwritten_v5 --seed 42
python3 -m piscine_forge.cli exam status
python3 -m piscine_forge.cli grademe
```

See `docs/STUDENT_USAGE.md` for the full student guide.
