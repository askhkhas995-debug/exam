"""BSQ map generator for project evaluator testing.

Generates valid and invalid BSQ maps with known or random solutions.
"""
from __future__ import annotations

import random
from typing import Literal


def generate_map(
    rows: int,
    cols: int,
    density: float = 0.2,
    seed: int | None = None,
    *,
    empty: str = ".",
    obstacle: str = "o",
    fill: str = "x",
) -> tuple[str, int]:
    """Generate a random BSQ map and return (map_string, largest_square_size).

    *density* is the proportion of obstacle cells (0.0 = empty, 1.0 = all
    obstacles).  The returned map includes the header line.
    """
    rng = random.Random(seed)
    grid: list[list[str]] = []
    for _ in range(rows):
        row: list[str] = []
        for _ in range(cols):
            row.append(obstacle if rng.random() < density else empty)
        grid.append(row)

    # Calculate largest square using DP
    dp = [[0] * cols for _ in range(rows)]
    max_size = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == empty:
                if r == 0 or c == 0:
                    dp[r][c] = 1
                else:
                    dp[r][c] = min(dp[r-1][c], dp[r][c-1], dp[r-1][c-1]) + 1
                max_size = max(max_size, dp[r][c])
            else:
                dp[r][c] = 0

    header = f"{rows}{empty}{obstacle}{fill}"
    lines = [header] + ["".join(row) for row in grid]
    return "\n".join(lines) + "\n", max_size


def solve_map(map_string: str) -> str:
    """Solve a BSQ map and return the filled output string."""
    lines = map_string.strip().split("\n")
    header = lines[0]
    # Parse header: last 3 chars are empty/obstacle/fill, rest is row count
    fill_char = header[-1]
    obs_char = header[-2]
    empty_char = header[-3]

    grid = [list(line) for line in lines[1:]]
    rows = len(grid)
    if rows == 0:
        return map_string
    cols = len(grid[0]) if grid else 0

    # DP for largest square
    dp = [[0] * cols for _ in range(rows)]
    max_size = 0
    max_r, max_c = 0, 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == empty_char:
                if r == 0 or c == 0:
                    dp[r][c] = 1
                else:
                    dp[r][c] = min(dp[r-1][c], dp[r][c-1], dp[r-1][c-1]) + 1
                if dp[r][c] > max_size:
                    max_size = dp[r][c]
                    max_r, max_c = r, c

    # Fill the largest square
    for r in range(max_r - max_size + 1, max_r + 1):
        for c in range(max_c - max_size + 1, max_c + 1):
            grid[r][c] = fill_char

    result_lines = [header] + ["".join(row) for row in grid]
    return "\n".join(result_lines) + "\n"


def generate_small_fixed() -> list[dict]:
    """Generate small fixed BSQ test cases with known solutions."""
    tests = []

    # 3x3 empty map
    map1 = "3.ox\n...\n...\n...\n"
    tests.append({
        "name": "3x3_empty",
        "map_content": map1,
        "args": ["MAP_FILE"],
        "stdout": solve_map(map1),
    })

    # 3x3 with obstacle
    map2 = "3.ox\n...\n.o.\n...\n"
    tests.append({
        "name": "3x3_obstacle",
        "map_content": map2,
        "args": ["MAP_FILE"],
        "stdout": solve_map(map2),
    })

    # 5x5 sparse
    map3 = "5.ox\n.....\n.o...\n.....\n...o.\n.....\n"
    tests.append({
        "name": "5x5_sparse",
        "map_content": map3,
        "args": ["MAP_FILE"],
        "stdout": solve_map(map3),
    })

    # 1x1
    map4 = "1.ox\n.\n"
    tests.append({
        "name": "1x1",
        "map_content": map4,
        "args": ["MAP_FILE"],
        "stdout": solve_map(map4),
    })

    return tests


def generate_large_random(seed: int = 42) -> list[dict]:
    """Generate large random BSQ maps."""
    tests = []

    # 100x100
    map_str, _ = generate_map(100, 100, density=0.3, seed=seed)
    tests.append({
        "name": "100x100_random",
        "map_content": map_str,
        "args": ["MAP_FILE"],
        "stdout": solve_map(map_str),
        "timeout": 10,
    })

    # 50x80
    map_str2, _ = generate_map(50, 80, density=0.15, seed=seed + 1)
    tests.append({
        "name": "50x80_sparse",
        "map_content": map_str2,
        "args": ["MAP_FILE"],
        "stdout": solve_map(map_str2),
        "timeout": 10,
    })

    return tests


def generate_invalid_maps() -> list[dict]:
    """Generate invalid BSQ map test cases."""
    tests = []

    # Missing header
    tests.append({
        "name": "no_header",
        "map_content": "...\n...\n",
        "args": ["MAP_FILE"],
        "expect_error": True,
    })

    # Wrong row count
    tests.append({
        "name": "wrong_row_count",
        "map_content": "5.ox\n...\n...\n",
        "args": ["MAP_FILE"],
        "expect_error": True,
    })

    # Inconsistent line lengths
    tests.append({
        "name": "inconsistent_lines",
        "map_content": "3.ox\n...\n....\n...\n",
        "args": ["MAP_FILE"],
        "expect_error": True,
    })

    # Empty file
    tests.append({
        "name": "empty_file",
        "map_content": "",
        "args": ["MAP_FILE"],
        "expect_error": True,
    })

    # Invalid characters
    tests.append({
        "name": "invalid_chars",
        "map_content": "3.ox\n...\n.X.\n...\n",
        "args": ["MAP_FILE"],
        "expect_error": True,
    })

    return tests
