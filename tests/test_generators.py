"""Tests for handwritten_v5 generators."""
from __future__ import annotations

import pytest

from piscine_forge.generators.handwritten import GENERATORS


class TestGeneratorDeterminism:
    """Every generator must produce identical output given the same seed."""

    @pytest.mark.parametrize("name", sorted(GENERATORS.keys()))
    def test_seeded_determinism(self, name):
        gen = GENERATORS[name]
        run1 = gen(seed=42)
        run2 = gen(seed=42)
        assert run1 == run2, f"{name} not deterministic with seed=42"

    @pytest.mark.parametrize("name", sorted(GENERATORS.keys()))
    def test_different_seeds_differ(self, name):
        gen = GENERATORS[name]
        run1 = gen(seed=42)
        run2 = gen(seed=99)
        # At least one test case should differ (the random ones)
        assert run1 != run2, f"{name} same output with different seeds"


class TestGeneratorOutput:
    """Every generator must return a list of valid test case dicts."""

    @pytest.mark.parametrize("name", sorted(GENERATORS.keys()))
    def test_returns_list(self, name):
        gen = GENERATORS[name]
        cases = gen(seed=42)
        assert isinstance(cases, list)
        assert len(cases) > 0

    @pytest.mark.parametrize("name", sorted(GENERATORS.keys()))
    def test_case_structure(self, name):
        gen = GENERATORS[name]
        for case in gen(seed=42):
            assert "args" in case, f"{name}: case missing 'args'"
            assert "stdout" in case, f"{name}: case missing 'stdout'"
            assert isinstance(case["args"], list)
            assert isinstance(case["stdout"], str)
            assert case["stdout"].endswith("\n"), f"{name}: stdout must end with newline"


class TestSpecificGenerators:
    def test_zigzag_basic(self):
        from piscine_forge.generators.handwritten import gen_zigzag
        cases = gen_zigzag(seed=42)
        # First fixed case
        assert cases[0] == {"args": ["hello"], "stdout": "HeLlO\n"}

    def test_rle_basic(self):
        from piscine_forge.generators.handwritten import gen_rle
        cases = gen_rle(seed=42)
        assert cases[0] == {"args": ["AAABBC"], "stdout": "3A2BC\n"}

    def test_rle_decode_basic(self):
        from piscine_forge.generators.handwritten import gen_rle_decode
        cases = gen_rle_decode(seed=42)
        assert cases[0] == {"args": ["3A2BC"], "stdout": "AAABBC\n"}

    def test_rle_large_repeat(self):
        from piscine_forge.generators.handwritten import gen_rle
        cases = gen_rle(seed=42)
        # Should have a case with 100 X's
        big_case = [c for c in cases if "100X" in c.get("stdout", "")]
        assert len(big_case) > 0

    def test_digit_root_correctness(self):
        from piscine_forge.generators.handwritten import gen_digit_root
        cases = gen_digit_root(seed=42)
        # 493193 -> 4+9+3+1+9+3=29 -> 2+9=11 -> 1+1=2
        found = [c for c in cases if c["args"] == ["493193"]]
        assert found
        assert found[0]["stdout"] == "2\n"

    def test_ping_pong_zero(self):
        from piscine_forge.generators.handwritten import gen_ping_pong
        cases = gen_ping_pong(seed=42)
        zero_case = [c for c in cases if c["args"] == ["0"]]
        assert zero_case
        assert zero_case[0]["stdout"] == "ping pong\n"

    def test_first_last_char_empty(self):
        from piscine_forge.generators.handwritten import gen_first_last_char
        cases = gen_first_last_char(seed=42)
        empty_cases = [c for c in cases if c["args"] == [] or c["args"] == [""]]
        assert len(empty_cases) >= 1
        for c in empty_cases:
            assert c["stdout"] == "\n"
