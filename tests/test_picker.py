"""Tests for deterministic seeded pool selection."""
from __future__ import annotations

from pathlib import Path

import pytest

from piscine_forge.loader import Repository
from piscine_forge.picker import curriculum_sequence, pick_from_pool


ROOT = Path(__file__).resolve().parents[1]


class TestPickerDeterminism:
    def test_same_seed_same_result(self):
        repo = Repository(ROOT)
        pool = repo.get_pool("handwritten_v5")
        picked1 = pick_from_pool(pool, seed=42)
        picked2 = pick_from_pool(pool, seed=42)
        assert picked1 == picked2

    def test_different_seed_different_result(self):
        repo = Repository(ROOT)
        pool = repo.get_pool("handwritten_v5")
        picked1 = pick_from_pool(pool, seed=42)
        picked2 = pick_from_pool(pool, seed=99)
        # At least one subject should differ
        ids1 = [p["subject_id"] for p in picked1]
        ids2 = [p["subject_id"] for p in picked2]
        assert ids1 != ids2

    def test_picks_one_per_level(self):
        repo = Repository(ROOT)
        pool = repo.get_pool("handwritten_v5")
        picked = pick_from_pool(pool, seed=42)
        levels = [p["level"] for p in picked]
        assert levels == sorted(set(levels))  # unique and ordered

    def test_seed_42_first_subject(self):
        repo = Repository(ROOT)
        pool = repo.get_pool("handwritten_v5")
        picked = pick_from_pool(pool, seed=42)
        assert picked[0]["subject_id"] == "first_last_char"


class TestCurriculumSequence:
    def test_piscine42_sequence(self):
        repo = Repository(ROOT)
        pool = repo.get_pool("piscine42_default")
        seq = curriculum_sequence(pool)
        assert len(seq) > 0
        # First module should be shell00
        assert seq[0]["module"] == "shell00"

