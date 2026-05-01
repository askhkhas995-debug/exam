# Implementation Notes

## Source of Truth

The rebuild starts from `pforge_handoff/pforge_handoff_package` and keeps its directory contract. The sibling extracted legacy directories were read as behavior references:

- `grademe 42 exam/n`
- `examshell-master`
- `ExamPoolRevanced-main`
- `42-School-Exam-Rank-02`
- `Subjects/*.pdf`, `Shell 00.pdf`, `Shell 01.pdf`

No original archive or handoff directory was modified.

## Architecture Decisions

- Current stable scope is terminal-only: Piscine modules/exercises/progress,
  Moulinette for Piscine, Grademe for Exam, the projects menu with local
  requirements/checks, local educational Vogsphere, and the terminal
  banner/menu.
- Normal Piscine, Friday exams, and Piscine27 are separate pool families. CLI commands map `pforge start piscine42` and `pforge start piscine27` to curriculum pools, while `pforge exam ...` uses versioned exam pools.
- Physical `meta.yml` subjects are loaded directly. `INDEX.yml` files are also loaded as virtual metadata so the normal Piscine and legacy exam pools can be listed and selected before every full subject is imported from PDFs or legacy archives.
- Student-visible workspace files are sanitized. `workspace/subject/meta.yml` omits correction profile paths, and correction files are not copied to `workspace/subject` or `workspace/rendu`.
- Norminette is wrapped, not reimplemented. Its result is recorded. Compile/test/forbidden failures can still surface explicitly so tracebacks identify the first actionable school-style failure.
- C function hidden mains are generated from `tests.yml` calls when available. This avoids exposing correction mains and keeps tests metadata-driven.
- Trace output preserves the old GradeMe idea of readable failure blocks, while adding structured `trace.json`.

## Legacy Conflict Handling

- Legacy GradeMe uses per-exercise `rendu/<exercise>/` paths. The rebuild grades `workspace/rendu/` by default but also accepts `workspace/rendu/<subject_id>/` if present.
- GradeMe adds artificial wait time and service telemetry. The rebuild intentionally omits both; it keeps session state and traces locally.
- ExamPoolRevanced generator scripts compile expected programs to generate outputs. The rebuild supports fixed metadata tests now and leaves richer generator adapters under `piscine_forge/generators/` as a future extension.
- Piscine PDFs are represented by module indexes and virtual metadata. Full per-exercise subject text import from PDFs is not implemented in this preview.

## Known Limitations

- PiscineForge is not official 42 software.
- Project Moulinette tests are local, reverse-engineered, reproducible trainer tests, not official 42 test suites or Moulinette clones. See `docs/PROJECT_TESTING_POLICY.md`.
- Piscine project entries are virtual metadata from `subjects/piscine/projects/projects/INDEX.yml`. Rush and Eval Expr projects have local preflight submission contracts. BSQ has local functional tests. Sastantua and Match-N-Match are explicitly metadata-incomplete.
- For legacy subjects (BSQ, Rush, Sastantua, etc.), the integration uses local project data. Local reference PDFs and metadata are stored under `resources/legacy_subjects/`. External repositories and links are catalog entries only. Remote downloads are disabled.

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
- `pforge project requirements <project>` inspects project metadata. `pforge project check <project>` inspects `workspace/rendu/` by default and can inspect the latest local submitted Vogsphere snapshot with `--source vog`.
- Shell evaluator supports exact output, contains checks, private fixture comparisons, executable checks, tar inspection, symlink, hardlink, permissions, timestamp, weird filename, Git commit, and `.gitignore` validators.
- Memory/sanitizer checks are not implemented yet.
- Legacy Rank02/Classic/Revanced pools are selectable and metadata-driven through indexes, but only subjects with tests/corrections can be fully graded.
- Piscine27 has 54 subjects from the handoff, but most tests remain placeholders except the implemented shell validation slice.
- `pforge moulinette summary` is a best-effort summary layer over current session/progress/trace data. It does not re-run complete modules and does not replace the single-subject evaluator.
- Full module correction, module auto-advance, and progress mutation from module-level checks are not implemented.
- `pforge vog` is a first local educational Vogsphere simulation. It snapshots only `workspace/rendu/` into `workspace/vogsphere/repos/<name>/` and stores local metadata/history/submission state in `workspace/vogsphere/state.json`.
- `pforge moulinette --source vog` and `pforge project check <project> --source vog` materialize the latest submitted local Vogsphere snapshot in a temporary directory. They do not mutate `workspace/rendu/`, `workspace/subject/`, or Vogsphere history. Grademe remains on `workspace/rendu/`.
- Exam/Grademe does not use Vogsphere. Any future local Exam Submit workflow must be separate from Vogsphere.
- Real Vogsphere/42 server integration is not implemented. The tool does not perform Kerberos, SSH, real upload, or `~/.ssh` operations.
- There is no GUI; the product surface is the CLI and terminal menu.
- Local educational packages may include correction fixtures under `resources/`; these are not copied into `workspace/subject/`, but they are not hidden from someone reading the repository. A public challenge distribution would need a different private-fixture packaging strategy.

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
