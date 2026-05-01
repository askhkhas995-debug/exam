# PiscineForge Student Usage

PiscineForge is a terminal-first practice tool, not official 42 software.
Public subjects are shown in `workspace/subject/`, and your submitted files go
in `workspace/rendu/`. Private correction data stays in the repository and is
not copied into the workspace.

PiscineForge is a Terminal UI, not a graphical GUI. The default visual style is
school-style and minimal: aligned labels, simple separators, and a few colors
only when your terminal supports them. Emojis are not used by default.

## Install

From the project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

If you do not install it yet, run the same commands with:

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

Use `--seed` with exam pools when you want the same selected exercises again.

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

## Work on an Exercise

Read the current subject:

```bash
pforge subject current
pforge current
pforge module list
pforge module current
pforge module progress
```

The subject file is copied to:

```txt
workspace/subject/subject.en.txt
```

Put your answer files in:

```txt
workspace/rendu/
```

Some evaluators also accept a nested folder named after the subject, for
example `workspace/rendu/ft_putchar/ft_putchar.c`, but the plain
`workspace/rendu/` folder is the normal path.

## Piscine: Run Moulinette

Start a Piscine, solve the current subject in `workspace/rendu/`, then run
Moulinette:

```bash
pforge correct
pforge moulinette
pforge moulinette summary
```

If the Moulinette result is `OK`, PiscineForge advances progress when another
subject is selected. If the result is `KO`, stay on the current subject, read
the trace, and try again.
`pforge correct` is mode-aware. In a Piscine session, `pforge grademe` remains
available only for compatibility and clearly warns that the active session uses
Moulinette.

Curriculum navigation is module-aware. `pforge current`, `pforge status`, and
the terminal menu show Pool, Module, Exercise, Subject, and Next so an exercise
such as `z` is shown as `Shell00 / ex00 / z`. Use `pforge module list` and
`pforge module progress` to inspect the active module without running
correction.

`pforge moulinette` corrects the current subject from `workspace/rendu/` by
default. `pforge moulinette --source vog` corrects the latest local submitted
Vogsphere snapshot without mutating `workspace/rendu/`. `pforge moulinette summary`
prints an optional Moulinette-style summary for the current module using the
current session, progress, and trace data. The summary command does not re-run
the whole module and does not replace the single-subject evaluator.
Full module correction is future work and is not implemented by this command.

## Exam: Run Grademe

Start an exam, solve the selected exercise in `workspace/rendu/`, then run
Grademe:

```bash
pforge grademe
pforge correct
```

If the Grademe result is `OK`, PiscineForge unlocks the next level when one is
available. If the result is `KO`, stay on the current level, read the trace, and
try again.
In an Exam session, `pforge moulinette` refuses and points you back to
`pforge grademe` or `pforge correct`.

Read the latest trace:

```bash
pforge trace
pforge trace --json
```

Trace files are generated under:

```txt
workspace/traces/
```

## Projects and Local Vogsphere

List the project entries that are actually scaffolded in this repository:

```bash
pforge projects
pforge project list
pforge project current
```

The current project menu is limited to the Piscine project module entries:
Rush00, Rush01, Rush02, Sastantua, Match-N-Match, Eval Expr, and BSQ.

Inspect requirements and preflight-check your current `workspace/rendu/`:

```bash
pforge project requirements bsq
pforge project check bsq
pforge project check bsq --source vog
pforge project references bsq
pforge project subject bsq
```

BSQ and Rush projects have local submission contracts. Project Moulinette tests
are local, reverse-engineered, reproducible trainer tests. They are not official
42 tests. See `docs/PROJECT_TESTING_POLICY.md` for details. Some project
entries are still metadata-incomplete; PiscineForge reports that directly
instead of inventing requirements. A project check is not full Moulinette: it
checks required files, forbidden files, Makefile presence, configured expected
binaries, unsafe symlinks, and the current contents of `workspace/rendu/`.

For legacy subjects like BSQ, Rush, and Sastantua, PiscineForge uses local project data. Local reference PDFs and metadata live in `resources/legacy_subjects/`. External repositories and links are catalog entries only. Remote downloads are disabled.

### Explicit Limitations and Boundaries

- **Project Moulinette is local-only.** It is not the official 42 Moulinette.
- It does not connect to real 42 services.
- Real Vogsphere, SSH, Kerberos, and official 42 service integration are out of scope.
- Remote downloads are disabled.
- Legacy repositories were used only during one-time preparation.
- PDFs under `resources/legacy_subjects/projects/<project>/` are local reference copies only.
- Existing built-in Piscine and exam subjects remain authoritative and are not touched.
- No solutions are imported, copied, displayed, or used.
- Project support status varies by project.


PiscineForge also includes a local educational Vogsphere simulation:

```bash
pforge vog status myrepo
pforge vog init myrepo
pforge vog commit -m "initial submit" myrepo
pforge vog log myrepo
pforge vog push myrepo
pforge vog submit myrepo
pforge vog history myrepo
```

This is not real Vogsphere. It snapshots only `workspace/rendu/` into
`workspace/vogsphere/repos/<name>/` and writes local state to
`workspace/vogsphere/state.json`. External services are not used; SSH,
Kerberos, real 42 servers, and `~/.ssh` are out of scope.
Project checks and Moulinette inspect `workspace/rendu/` by default. They can
use the latest submitted local Vogsphere snapshot only when `--source vog` is
passed. Grademe continues to use `workspace/rendu/`; Exam does not use
Vogsphere.

## Check Progress

Show the current subject:

```bash
pforge current
```

Show status and time:

```bash
pforge status
```

Show history:

```bash
pforge history
pforge history failed
pforge history completed
pforge history attempts
```

Exam timers are real only when the exam pool defines a duration. If no duration
is configured, PiscineForge prints:

```txt
Time remaining: not configured
```

## Themes and Colors

The default theme is `official`.

```bash
PFORGE_THEME=official pforge menu
PFORGE_THEME=tokyo-night pforge menu
PFORGE_THEME=gruvbox pforge menu
PFORGE_THEME=plain pforge menu
```

`PFORGE_THEME=graphbox` is accepted as an alias for `gruvbox`.

Colors are only used when stdout is a TTY. Tests, pipes, and redirected output
stay colorless. Disable colors explicitly with either:

```bash
NO_COLOR=1 pforge status
PFORGE_THEME=plain pforge status
```

PiscineForge cannot set your terminal font from Python. Configure fonts in your
terminal app. Readable terminal fonts include:

- JetBrains Mono
- IBM Plex Mono
- Hack
- Fira Code
- MesloLGS

Nerd Fonts are optional and not required.

## Reset Safely

Reset commands only touch generated files under `workspace/`. They never delete
`subjects/`, `corrections/`, `pools/`, `config/`, source code, tests, or private
correction data.

```bash
pforge reset session
pforge reset progress
pforge reset traces
pforge reset all
```

`reset progress`, `reset traces`, and `reset all` ask for confirmation unless
you pass `--yes`:

```bash
pforge reset traces --yes
```

`reset all` keeps `workspace/rendu/` by default, so student solutions are not
deleted.

## Safety and Scope

PiscineForge is an educational local simulator, not a secure remote judge and
not official 42 software. The local repo may contain correction fixtures under
`resources/` and private correction metadata under `corrections/`; these files
are not copied into the student-visible `workspace/subject/` directory. This
protects the student workspace, but it is not secure against someone reading
the repository. If PiscineForge is packaged as a public challenge environment
later, private fixtures should be handled with a different distribution
strategy.

The Vogsphere/Git layer is local educational simulation only. PiscineForge does
not connect to official 42 services, does not use Kerberos, does not upload anywhere,
does not read or modify your SSH configuration, and does not provide a GUI.
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
