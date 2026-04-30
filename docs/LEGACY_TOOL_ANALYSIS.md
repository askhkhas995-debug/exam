# Legacy Tool Analysis

## Analyzed Inputs

- `grademe 42 exam/n/.system/*.cpp` and `.system/*.sh`
- `examshell-master/level*/`
- `ExamPoolRevanced-main/Exam00`, `Exam01`, `Exam02`, `ExamFinal`
- `42-School-Exam-Rank-02/Level 1` through `Level 4`
- Piscine PDFs: Shell00, Shell01, C00-C13

The workspace contained extracted directories rather than compressed archive files, so analysis used those directories directly.

## GradeMe

Relevant behavior found:

- Random exercise selection by level, with an optional removal of already-successful exercises.
- Session-like state with current level, assignment attempt count, success history, and cooldown before regrading.
- A public `subjects/subject.en.txt` and private `.system/grading/` separation.
- Student work expected in `rendu/`, with old UI messaging commonly pointing to `rendu/<exercise>/`.
- Bash correction scripts compile source and student submissions, run both, compare `cat -e` output, detect timeouts, and write a human traceback.
- Failure keeps the same assignment and increments attempt/cooldown. Success advances level and copies accepted work to `success/`.

Reused in PiscineForge:

- Session-first terminal flow.
- Current subject display and `workspace/rendu/` submission workflow.
- Strict compile/test/trace pipeline.
- Readable traceback blocks with expected and actual outputs.
- Success advancement through selected exam levels.

Rewritten:

- Bash scripts are replaced by Python evaluators using metadata.
- Network telemetry, VIP features, cooldowns, and cheat commands are omitted.
- Traceback is now paired with structured JSON.

## ExamShell / Classic Pools

Relevant behavior found:

- Level-based pools with one random assignment per level.
- Classic low-level C exercises such as `aff_a`, `first_word`, `repeat_alpha`, `ft_strlen`, `inter`, `union`, `ft_range`, `ft_itoa`, and list exercises.
- Subjects are public text files separated from correction behavior.

Reused in PiscineForge:

- `classic_v1` and `rank02_v2` pool shape.
- Incremental exam path separate from Piscine curriculum.
- Virtual metadata from `INDEX.yml` for legacy subject banks.

## ExamPoolRevanced / Deepthought-Style Corrections

Relevant behavior found:

- `profile.yml` files specify assignment name, user files, common correction files, whitelist/allowed functions, and test counts.
- Generator scripts compile an expected program and create randomized tests.
- Guidelines state exact filenames, automatic correction, allowed functions, and `clang/gcc -Wall -Wextra -Werror`.
- Folder review tools check subject/correction mismatches and missing subject files.

Reused in PiscineForge:

- Correction profiles stay private under `corrections/`.
- User files and hidden/common correction files are metadata concepts.
- Fixed and generated tests are separate extension points.
- Allowed/forbidden function policy is explicit in metadata.

Rewritten:

- Python generator scripts are not imported wholesale.
- The first implementation supports fixed tests and generated hidden mains; generator adapters are left as a future extension.

## 42-School-Exam-Rank-02

Relevant behavior found:

- Four-level rank02-style exercise pools.
- README describes random selection, reset-on-fail behavior, `subjects`, `rendu`, `traces`, and `grademe`.
- Exercise README files provide subject text and reference solutions.

Reused in PiscineForge:

- `rank02_v2` and `1337_2025_v4` versioned exam pools.
- Session paths and command vocabulary.

## Piscine PDFs

Relevant behavior found:

- Shell00 and Shell01 explicitly require `/bin/sh`, exact filenames, executable behavior, and no extra files.
- C00-C13 PDF subjects define the continuous Piscine curriculum.
- PDF extraction confirmed module coverage and page counts.

Reused in PiscineForge:

- Normal Piscine path includes Shell00, Shell01, C00-C13, and projects through YAML modules.
- Shell evaluator uses `/bin/sh` and strict expected file checks.

## Follow-Up Work

- Import full PDF exercise texts into per-subject folders.
- Port selected legacy generated tests into `tests.yml` or generator adapters.
- Add tar/symlink/hardlink/timestamp shell validators.
- Add BSQ map generation and project-scale memory/time checks.
