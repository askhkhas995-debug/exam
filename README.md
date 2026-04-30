# PiscineForge Rebuilt

PiscineForge is a terminal-first 42 Piscine and Friday Exam practice simulator.
It is not official 42 software. It keeps public subjects under `subjects/`,
private correction profiles under `corrections/`, pool selection under
`pools/`, and student work under `workspace/rendu/`.
The interface is a minimal Terminal UI, not a GUI. It uses aligned text and simple ANSI colors only when stdout is a TTY.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pforge doctor
```

On systems with an externally managed Python installation, use a virtual environment as shown above.

## Common Commands

```bash
pforge validate
pforge doctor
pforge version
pforge
pforge menu
pforge list subjects
pforge list pools
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
pforge reset session
pforge finish
```

Work only in `workspace/rendu/`. The active subject is copied or rendered into `workspace/subject/`. Corrections are never copied into the workspace.
See `docs/STUDENT_USAGE.md` for reset safety and the full student workflow.

## Correction Modes

Piscine/curriculum sessions use **Moulinette** terminology. Start a Piscine,
solve the current subject in `workspace/rendu/`, then run:

```bash
pforge correct
pforge moulinette
pforge moulinette summary
```

An OK Moulinette result advances progress when another subject is selected. The
Moulinette trace is written under `workspace/traces/`.
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

Exam sessions use **Grademe** terminology. Start an exam, solve the selected
exercise in `workspace/rendu/`, then run:

```bash
pforge grademe
pforge correct
```

An OK Grademe result unlocks the next level when one is available. The Grademe
trace is written under `workspace/traces/`.
In an Exam session, `pforge moulinette` refuses and points you back to
`pforge grademe` or `pforge correct`.

## Projects and Local Vogsphere

`pforge projects` lists only projects that are actually scaffolded in the
current repository. Today that means the Piscine project module entries:
Rush00, Rush01, Rush02, Sastantua, Match-N-Match, Eval Expr, and BSQ.

Use the project preflight commands to inspect the current local submission
contract and check `workspace/rendu/` before running full correction:

```bash
pforge project list
pforge project requirements bsq
pforge project check bsq
```

BSQ and Rush projects have preflight submission contracts for the current local
simulator. Sastantua, Match-N-Match, and Eval Expr are still reported honestly
as metadata-incomplete until detailed submission contracts are added.

`pforge vog` is a local educational Vogsphere simulation. It snapshots only
`workspace/rendu/` into `workspace/vogsphere/repos/<name>/` and stores local
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

Themes are selected with `PFORGE_THEME=official`, `tokyo-night`, `gruvbox`, or `plain`; `graphbox` maps to `gruvbox`. Use `NO_COLOR=1` or `PFORGE_THEME=plain` to disable colors.

## Safety and Packaging Notes

This repository is an educational local simulator, not a secure remote judge
and not official 42 software.
The local package may contain correction fixtures under `resources/` and
private correction metadata under `corrections/`; these are not copied into
`workspace/subject/` or `workspace/rendu/`. This protects the student-visible
workspace, but it is not secure against someone reading the repository. A
public challenge distribution would need a different packaging strategy for
private fixtures.

The Vogsphere layer is local educational simulation only. PiscineForge does not
use Kerberos, does not upload anywhere, does not modify SSH configuration, does
not contact real 42 infrastructure, and does not provide a GUI.

## Implemented Evaluator Slices

- `c_program`: expected file checks, extra-file rejection, Norminette wrapper, forbidden scanner, `gcc -Wall -Wextra -Werror`, exact stdout comparison, timeouts, traces.
- `c_function`: hidden main generation from metadata tests, main rejection, return/stdout testing support, forbidden scanner, traces.
- `shell`: `/bin/sh` syntax and execution, expected file checks, stdout exact/contains checks, fixture files, traces.
- `project`: Makefile presence and `make` execution, Norminette/forbidden hooks.

See `BUILD_REPORT.md`, `TEST_REPORT.md`, and `docs/IMPLEMENTATION_NOTES.md` for details and limitations.
# exam
