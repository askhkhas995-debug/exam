# Test Report

## Commands Run

```bash
python3 -m piscine_forge.cli validate
python3 -m piscine_forge.cli list pools
python3 -m piscine_forge.cli list subjects
python3 -m piscine_forge.cli exam handwritten_v5 --seed 42
python3 -m piscine_forge.cli subject current
python3 -m piscine_forge.cli grademe
python3 -m piscine_forge.cli grademe --subject print_nth_char
python3 -m piscine_forge.cli grademe --subject p27_pwd_tree
python3 -m piscine_forge.cli grademe --subject alpha_index_case
python3 -m piscine_forge.cli trace
python3 -m compileall piscine_forge
python3 -m pytest -q
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pforge validate
```

## Results

- `pforge validate`: passed.
- `pforge list pools`: passed and showed all required pool IDs.
- `pforge list subjects`: passed and listed 298 loaded subjects, including virtual index subjects.
- `pforge exam handwritten_v5 --seed 42`: deterministic session created with `first_last_char`, `zigzag`, `snake_to_camel`, `print_nth_char`, `rle_decode`.
- `pforge start piscine42`: session starts at Shell00 subject `z`.
- `pforge start piscine27`: session starts at `p27_pwd_tree`.
- C program grading: passed with `first_last_char`.
- C function grading: passed with `print_nth_char`.
- Shell grading: passed with `p27_pwd_tree`.
- Missing files: detected.
- Compile errors: detected.
- Wrong stdout: detected.
- Forbidden functions: detected.
- `workspace/traces/trace.json`: generated.
- `workspace/traces/traceback.txt`: generated.
- `python3 -m compileall piscine_forge`: passed.
- `python3 -m pytest -q`: `5 passed in 45.43s`.
- Direct system `pip install -e .` was blocked by PEP 668 externally-managed Python. Virtualenv install passed.

## Failing Tests

None in the automated suite.

## Missing Features

- Full PDF text import and complete correction banks are not finished.
- Project/BSQ evaluator is not yet complete.
- Shell special-object validators are not yet complete.
