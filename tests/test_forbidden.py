"""Tests for forbidden function detection."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from piscine_forge.forbidden import contains_main, scan_files


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory(prefix="pforge-test-") as d:
        yield Path(d)


class TestForbiddenFunctions:
    def test_detects_printf(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('#include <stdio.h>\nint main(void) { printf("hello"); return 0; }\n')
        result = scan_files([f], ["printf"])
        assert not result.ok
        assert "printf" in result.hits

    def test_ignores_printf_in_comments(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('// printf("hello")\nint main(void) { return 0; }\n')
        result = scan_files([f], ["printf"])
        assert result.ok

    def test_ignores_printf_in_block_comments(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('/* printf("hello") */\nint main(void) { return 0; }\n')
        result = scan_files([f], ["printf"])
        assert result.ok

    def test_ignores_printf_in_strings(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('int main(void) { char *s = "printf(x)"; return 0; }\n')
        result = scan_files([f], ["printf"])
        assert result.ok

    def test_detects_puts(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('int main(void) { puts("hello"); return 0; }\n')
        result = scan_files([f], ["puts"])
        assert not result.ok

    def test_no_false_positive_on_fputs(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('int main(void) { fputs("hello", stdout); return 0; }\n')
        result = scan_files([f], ["puts"])
        # fputs should NOT match puts because of \b word boundary
        assert result.ok

    def test_empty_forbidden_list(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('#include <stdio.h>\nint main(void) { printf("hello"); return 0; }\n')
        result = scan_files([f], [])
        assert result.ok

    def test_multiple_files(self, tmpdir):
        f1 = tmpdir / "a.c"
        f1.write_text('void foo(void) { write(1, "a", 1); }\n')
        f2 = tmpdir / "b.c"
        f2.write_text('void bar(void) { printf("b"); }\n')
        result = scan_files([f1, f2], ["printf"])
        assert not result.ok
        assert str(f2) in result.hits["printf"]


class TestContainsMain:
    def test_detects_main(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('int main(void) { return 0; }\n')
        assert contains_main(f)

    def test_no_main(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('void ft_putchar(char c) { write(1, &c, 1); }\n')
        assert not contains_main(f)

    def test_main_in_comment(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('// int main(void)\nvoid foo(void) {}\n')
        assert not contains_main(f)

    def test_main_in_string(self, tmpdir):
        f = tmpdir / "test.c"
        f.write_text('void foo(void) { char *s = "main(void)"; }\n')
        assert not contains_main(f)
