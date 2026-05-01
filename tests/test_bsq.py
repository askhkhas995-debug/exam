"""Tests for BSQ map generator."""
from __future__ import annotations

from pathlib import Path

import pytest

from piscine_forge.generators.bsq import (
    generate_invalid_maps,
    generate_large_random,
    generate_map,
    generate_small_fixed,
    solve_map,
)


class TestMapGeneration:
    def test_basic_generation(self):
        map_str, max_size = generate_map(5, 5, density=0.0, seed=42)
        assert max_size == 5  # empty 5x5 → largest square is 5
        assert map_str.startswith("5")

    def test_seeded_determinism(self):
        m1, s1 = generate_map(10, 10, density=0.3, seed=42)
        m2, s2 = generate_map(10, 10, density=0.3, seed=42)
        assert m1 == m2
        assert s1 == s2

    def test_different_seeds_differ(self):
        m1, _ = generate_map(10, 10, density=0.3, seed=42)
        m2, _ = generate_map(10, 10, density=0.3, seed=99)
        assert m1 != m2

    def test_full_density(self):
        map_str, max_size = generate_map(5, 5, density=1.0, seed=42)
        assert max_size == 0  # all obstacles

    def test_1x1_map(self):
        map_str, max_size = generate_map(1, 1, density=0.0, seed=42)
        assert max_size == 1

    def test_header_format(self):
        map_str, _ = generate_map(10, 20, density=0.2, seed=42)
        lines = map_str.strip().split("\n")
        header = lines[0]
        assert header == "10.ox"
        assert len(lines) == 11  # header + 10 rows

    def test_line_lengths(self):
        map_str, _ = generate_map(10, 20, density=0.2, seed=42)
        lines = map_str.strip().split("\n")
        for line in lines[1:]:
            assert len(line) == 20


class TestMapSolver:
    def test_solve_empty_3x3(self):
        map_str = "3.ox\n...\n...\n...\n"
        solved = solve_map(map_str)
        assert "x" in solved  # should have filled squares
        lines = solved.strip().split("\n")
        assert len(lines) == 4  # header + 3 rows

    def test_solve_1x1(self):
        map_str = "1.ox\n.\n"
        solved = solve_map(map_str)
        assert "x" in solved

    def test_solve_preserves_obstacles(self):
        map_str = "3.ox\n.o.\n...\no..\n"
        solved = solve_map(map_str)
        lines = solved.strip().split("\n")
        # Obstacle at (0,1) should remain
        assert lines[1][1] == "o"

    def test_roundtrip_consistency(self):
        map_str, max_size = generate_map(8, 8, density=0.2, seed=42)
        solved = solve_map(map_str)
        # Count fill chars only in data lines (skip header)
        data_lines = solved.strip().split("\n")[1:]
        fill_count = sum(line.count("x") for line in data_lines)
        assert fill_count == max_size * max_size


class TestSmallFixed:
    def test_generates_cases(self):
        cases = generate_small_fixed()
        assert len(cases) >= 3
        for case in cases:
            assert "name" in case
            assert "map_content" in case
            assert "stdout" in case

    def test_solved_output(self):
        cases = generate_small_fixed()
        for case in cases:
            assert "x" in case["stdout"] or case["map_content"].count(".") == 0


class TestLargeRandom:
    def test_generates_cases(self):
        cases = generate_large_random(seed=42)
        assert len(cases) >= 1
        for case in cases:
            assert "name" in case
            assert "map_content" in case
            assert "timeout" in case


class TestInvalidMaps:
    def test_generates_cases(self):
        cases = generate_invalid_maps()
        assert len(cases) >= 3
        for case in cases:
            assert case.get("expect_error") is True

    def test_project_profile_requires_stderr_and_failure_for_invalid_maps(self):
        import yaml

        data = yaml.safe_load((Path(__file__).resolve().parents[1] / "corrections" / "projects" / "bsq" / "tests.yml").read_text(encoding="utf-8"))
        invalid_cases = [case for case in data["fixed_tests"] if case["name"].startswith("invalid_")]
        assert invalid_cases
        for case in invalid_cases:
            assert case["expect_error"] is True
            assert case["exit_code"] == 1
            assert case["expected_stderr"] == "map error\n"
