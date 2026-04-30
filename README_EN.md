# PiscineForge

PiscineForge is a terminal-first 42 Piscine and Friday Exam practice simulator.
It is not official 42 software. It is a Terminal UI, not a GUI. The default
style is school-style and minimal: aligned labels, calm separators, and no
emojis by default.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pforge doctor
```

Without installation, use:

```bash
python3 -m piscine_forge.cli --help
```

## Common Commands

```bash
pforge
pforge doctor
pforge version
pforge menu
pforge start piscine42
pforge start piscine27
pforge projects
pforge project list
pforge project requirements bsq
pforge project check bsq
pforge vog status
pforge vog init myrepo
pforge vog commit -m "initial submit" myrepo
pforge vog push myrepo
pforge vog submit myrepo
pforge exam handwritten_v5 --seed 42
pforge subject current
pforge current
pforge module list
pforge module current
pforge module progress
pforge correct
pforge moulinette
pforge moulinette summary
pforge grademe
pforge trace
pforge status
pforge history
```

Read subjects in `workspace/subject/` and put your files in
`workspace/rendu/`. Corrections, hidden mains, and private tests are not copied
to the student workspace.

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

BSQ and Rush projects have preflight submission contracts for the current local
simulator. Sastantua, Match-N-Match, and Eval Expr are still reported honestly
as metadata-incomplete until detailed submission contracts are added.

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

This layer is not required by Moulinette or Grademe yet. It does not use
network access, SSH, Kerberos, real 42 servers, or `~/.ssh`.
Project checks still inspect `workspace/rendu/`; they do not read from
Vogsphere snapshots yet.

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
not contact real 42 infrastructure, and does not provide a GUI.

See `docs/STUDENT_USAGE.md` for the full student guide.
