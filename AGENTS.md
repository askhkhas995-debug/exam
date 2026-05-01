# PiscineForge Agent Instructions

## Project scope

PiscineForge is a terminal-only 42-style training simulator.

Current focus:
- Piscine modules/exercises/progress
- Existing Piscine projects
- Exam / ExamShell / Grademe terminal experience
- Local educational Vogsphere layer
- Project requirements and submission checks
- Terminal banner/menu

Do not add unless explicitly requested:
- GUI
- schedule/calendar
- level/XP
- learning outcomes
- Black Hole
- real 42/Vogsphere integration
- real SSH/Kerberos/service flows

## Core concepts

- Piscine uses Moulinette.
- Exam uses Grademe.
- Projects use project requirements/checks and Project Moulinette where supported.
- Vogsphere is local educational storage only.
- Default correction reads `workspace/rendu/`.
- `--source vog` may use a local submitted Vogsphere snapshot for Moulinette/project preflight only.
- Grademe and Exam must not use Vogsphere; they read `workspace/rendu/`.
- Any future local Exam Submit workflow must be separate from Vogsphere.
- Some virtual project metadata may remain incomplete.
- Do not mix Exam Grademe with Piscine Moulinette.
- Do not rewrite the evaluator unless explicitly requested.

## Safety rules

- No GUI or heavy UI dependencies.
- No remote service calls.
- Do not touch `~/.ssh`.
- Do not use Kerberos.
- Do not connect to real 42 servers.
- Do not expose hidden tests or correction fixtures to `workspace/subject`.
- Do not copy `workspace/subject` into Vogsphere snapshots.
- Keep terminal output compact and readable.
- Respect `NO_COLOR` and plain output behavior.
- No ANSI codes in JSON/trace files.

## Important commands

Run before final report:

```bash
python3 -m compileall -q piscine_forge
python3 -m pytest -q
python3 -m piscine_forge.cli validate
```

Useful smoke checks:

```bash
python3 -m piscine_forge.cli menu
python3 -m piscine_forge.cli projects
python3 -m piscine_forge.cli project list
python3 -m piscine_forge.cli vog status
python3 -m piscine_forge.cli exam handwritten_v5 --seed 42
python3 -m piscine_forge.cli exam status
python3 -m piscine_forge.cli grademe
```

## Workflow expectations

Before implementing:
1. Inspect current code and tests.
2. Run focused tests for the area being edited.
3. Preserve existing CLI behavior.
4. Add focused tests for changed behavior when risk warrants it.
5. Run the full required validation commands.

When reporting:
- list files changed
- explain behavior changed
- include tests run and final result
- mention remaining limitations
