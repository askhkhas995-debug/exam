# Build Report

## Implemented

- Clean project directory: `piscine-forge-rebuilt/`.
- Metadata-driven loader for physical `meta.yml` subjects and virtual `INDEX.yml` subjects.
- Pool loader and validator, including missing subject reference detection.
- CLI commands: `validate`, `list subjects`, `list pools`, `start piscine42`, `start piscine27`, `exam`, `subject current`, `subject set`, `grademe`, `trace`, `status`, `finish`.
- Deterministic seeded exam sessions.
- Workspace/session system under `workspace/subject`, `workspace/rendu`, and `workspace/traces`.
- C program evaluator with expected files, extra-file rejection, Norminette wrapper, forbidden scanner, compile, timeout, exact stdout comparison, and traces.
- C function evaluator with main rejection and metadata-driven hidden main generation.
- Shell evaluator with `/bin/sh` syntax/run checks and fixture/output validation.
- Minimal project evaluator with Makefile and `make` support.
- Versioned exam pools for `classic_v1`, `rank02_v2`, `revanced_v3`, `1337_2025_v4`, and `handwritten_v5`.
- Normal Piscine pool covering Shell00, Shell01, C00-C13, and projects.
- Required docs: `docs/IMPLEMENTATION_NOTES.md`, `docs/LEGACY_TOOL_ANALYSIS.md`, `BUILD_REPORT.md`, `TEST_REPORT.md`.

## Archives Analyzed

- Handoff package: `pforge_handoff/pforge_handoff_package`.
- Legacy GradeMe: `grademe 42 exam/n`.
- Legacy ExamShell: `examshell-master`.
- Legacy Revanced/Deepthought-style pools: `ExamPoolRevanced-main`.
- Rank02 archive: `42-School-Exam-Rank-02`.
- Piscine PDFs: `Shell 00.pdf`, `Shell 01.pdf`, and `Subjects/C 00.pdf` through `Subjects/C 13.pdf`.

## Legacy Logic Reused

- Session-based terminal workflow.
- Separate public subject and private correction areas.
- Random level-based exam selection.
- Strict filename and output comparisons.
- Hidden-main function correction model.
- Readable tracebacks with expected/actual output.
- `/bin/sh` shell execution for shell subjects.

## Rewritten

- Bash correction scripts and C++ menu/session code were replaced by Python modules.
- Hardcoded grading scripts were replaced by metadata-driven dispatch.
- Tracebacks were kept readable but paired with structured JSON.
- Network telemetry, VIP, cooldown, and cheat features were not carried over.

## TODO

- Full PDF subject import for every Piscine exercise.
- Full tar/symlink/hardlink/timestamp/git shell validation.
- Rich generated test adapters from Revanced generator scripts.
- BSQ map generator and large project correction.
- Sanitizer/memory checks.
- More Piscine27 fixed tests and progressive hint enforcement.

## Known Limitations

- Many legacy/indexed subjects are selectable but not fully gradable until tests/corrections are imported.
- Norminette is delegated to the installed command. If missing, it is recorded as skipped.
- Project evaluator is intentionally minimal.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pforge validate
```

## Usage

```bash
pforge exam handwritten_v5 --seed 42
pforge subject current
# write files in workspace/rendu/
pforge grademe
pforge trace
```
