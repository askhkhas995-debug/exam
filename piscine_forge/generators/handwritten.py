"""Random test generators for handwritten_v5 exam subjects.

Each generator takes a ``seed`` and returns a list of test-case dicts
compatible with the fixed_tests format::

    [{"args": ["input"], "stdout": "expected\\n"}, ...]
"""
from __future__ import annotations

import random
import string


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _rng(seed: int | None) -> random.Random:
    return random.Random(seed)


def _rand_word(rng: random.Random, minlen: int = 2, maxlen: int = 8) -> str:
    length = rng.randint(minlen, maxlen)
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(length))


def _rand_sentence(rng: random.Random, words: int = 3) -> str:
    return " ".join(_rand_word(rng) for _ in range(words))


# ---------------------------------------------------------------------------
# zigzag
# ---------------------------------------------------------------------------

def _zigzag(s: str) -> str:
    return "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(s))


def gen_zigzag(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["hello"], "stdout": "HeLlO\n"},
        {"args": ["a b c"], "stdout": "A B C\n"},  # space keeps index
        {"args": [""], "stdout": "\n"},
        {"args": ["A"], "stdout": "A\n"},
    ]
    for _ in range(6):
        s = _rand_sentence(rng, rng.randint(1, 4))
        cases.append({"args": [s], "stdout": _zigzag(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# index_case
# ---------------------------------------------------------------------------

def _index_case(s: str) -> str:
    out = []
    idx = 0
    for c in s:
        if c.isalpha():
            out.append(c.upper() if idx % 2 == 0 else c.lower())
            idx += 1
        else:
            out.append(c)
    return "".join(out)


def gen_index_case(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": [""], "stdout": "\n"},
        {"args": ["a"], "stdout": "A\n"},
        {"args": ["hello world"], "stdout": _index_case("hello world") + "\n"},
    ]
    for _ in range(7):
        s = _rand_sentence(rng, rng.randint(1, 3))
        cases.append({"args": [s], "stdout": _index_case(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# alpha_index_case – uppercase at even alphabetic index
# ---------------------------------------------------------------------------

def _alpha_index_case(s: str) -> str:
    """Same as index_case but only counting alpha positions."""
    return _index_case(s)  # they are logically the same spec


def gen_alpha_index_case(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": [""], "stdout": "\n"},
        {"args": ["a"], "stdout": "A\n"},
        {"args": ["Ab Cd!"], "stdout": _alpha_index_case("Ab Cd!") + "\n"},
    ]
    for _ in range(7):
        s = _rand_sentence(rng, rng.randint(1, 4))
        cases.append({"args": [s], "stdout": _alpha_index_case(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# alt_case
# ---------------------------------------------------------------------------

def _alt_case(s: str) -> str:
    """Alternate case per word: first char upper, second lower, etc."""
    out = []
    for word in s.split(" "):
        alt = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(word))
        out.append(alt)
    return " ".join(out)


def gen_alt_case(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": [""], "stdout": "\n"},
        {"args": ["a"], "stdout": "A\n"},
        {"args": ["abc def"], "stdout": _alt_case("abc def") + "\n"},
    ]
    for _ in range(7):
        s = _rand_sentence(rng, rng.randint(2, 4))
        cases.append({"args": [s], "stdout": _alt_case(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# snake_to_camel
# ---------------------------------------------------------------------------

def _snake_to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def gen_snake_to_camel(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": [""], "stdout": "\n"},
        {"args": ["a"], "stdout": "a\n"},
        {"args": ["hello_world"], "stdout": "helloWorld\n"},
        {"args": ["_leading"], "stdout": "Leading\n"},
        {"args": ["trailing_"], "stdout": "trailing\n"},
    ]
    for _ in range(5):
        words = [_rand_word(rng) for _ in range(rng.randint(2, 4))]
        snake = "_".join(words)
        cases.append({"args": [snake], "stdout": _snake_to_camel(snake) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# camel_to_snake
# ---------------------------------------------------------------------------

def _camel_to_snake(s: str) -> str:
    result: list[str] = []
    for c in s:
        if c.isupper() and result:
            result.append("_")
        result.append(c.lower())
    return "".join(result)


def gen_camel_to_snake(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": [""], "stdout": "\n"},
        {"args": ["a"], "stdout": "a\n"},
        {"args": ["helloWorld"], "stdout": "hello_world\n"},
        {"args": ["CamelCase"], "stdout": "_camel_case\n"},
    ]
    for _ in range(6):
        words = [_rand_word(rng) for _ in range(rng.randint(2, 4))]
        camel = words[0] + "".join(w.capitalize() for w in words[1:])
        cases.append({"args": [camel], "stdout": _camel_to_snake(camel) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# snake_case (spaces to underscores)
# ---------------------------------------------------------------------------

def _snake_case(s: str) -> str:
    return s.replace(" ", "_").lower()


def gen_snake_case(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": [""], "stdout": "\n"},
        {"args": ["a"], "stdout": "a\n"},
        {"args": ["Hello World"], "stdout": "hello_world\n"},
        {"args": ["  two  spaces  "], "stdout": "__two__spaces__\n"},
    ]
    for _ in range(6):
        s = _rand_sentence(rng, rng.randint(2, 4))
        cases.append({"args": [s], "stdout": _snake_case(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# ping_pong
# ---------------------------------------------------------------------------

def _ping_pong(n: int) -> str:
    if n % 15 == 0:
        return "ping pong"
    if n % 3 == 0:
        return "ping"
    if n % 5 == 0:
        return "pong"
    return str(n)


def gen_ping_pong(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = []
    # Fixed cases
    for n in [1, 3, 5, 15, 0, -1]:
        cases.append({"args": [str(n)], "stdout": _ping_pong(n) + "\n"})
    # Random
    for _ in range(4):
        n = rng.randint(1, 200)
        cases.append({"args": [str(n)], "stdout": _ping_pong(n) + "\n"})
    # Edge: no args
    cases.append({"args": [], "stdout": "\n"})
    return cases


# ---------------------------------------------------------------------------
# nth_remove – remove every Nth character
# ---------------------------------------------------------------------------

def _nth_remove(s: str, n: int) -> str:
    if n <= 0:
        return s
    return "".join(c for i, c in enumerate(s) if (i + 1) % n != 0)


def gen_nth_remove(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["hello", "2"], "stdout": "hlo\n"},
        {"args": ["", "3"], "stdout": "\n"},
        {"args": ["a", "1"], "stdout": "\n"},
    ]
    for _ in range(7):
        s = _rand_word(rng, 5, 15)
        n = rng.randint(1, 5)
        cases.append({"args": [s, str(n)], "stdout": _nth_remove(s, n) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# nth_reverse – reverse chunks of N
# ---------------------------------------------------------------------------

def _nth_reverse(s: str, n: int) -> str:
    if n <= 0:
        return s
    result: list[str] = []
    for i in range(0, len(s), n):
        chunk = s[i:i + n]
        result.append(chunk[::-1])
    return "".join(result)


def gen_nth_reverse(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["hello", "3"], "stdout": _nth_reverse("hello", 3) + "\n"},
        {"args": ["", "2"], "stdout": "\n"},
        {"args": ["a", "1"], "stdout": "a\n"},
    ]
    for _ in range(7):
        s = _rand_word(rng, 5, 15)
        n = rng.randint(1, 5)
        cases.append({"args": [s, str(n)], "stdout": _nth_reverse(s, n) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# print_nth_char
# ---------------------------------------------------------------------------

def _print_nth_char(s: str, n: int) -> str:
    if n <= 0:
        return ""
    return "".join(s[i] for i in range(n - 1, len(s), n))


def gen_print_nth_char(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["Hello World!", "3"], "stdout": "loWl\n"},
        {"args": ["", "2"], "stdout": "\n"},
        {"args": ["a", "1"], "stdout": "a\n"},
    ]
    for _ in range(7):
        s = _rand_sentence(rng, rng.randint(2, 4))
        n = rng.randint(1, 4)
        cases.append({"args": [s, str(n)], "stdout": _print_nth_char(s, n) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# first_last_char
# ---------------------------------------------------------------------------

def _first_last_char(s: str) -> str:
    if not s:
        return ""
    return s[0] + s[-1]


def gen_first_last_char(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["Hello"], "stdout": "Ho\n"},
        {"args": ["a"], "stdout": "aa\n"},
        {"args": [], "stdout": "\n"},
        {"args": [""], "stdout": "\n"},
    ]
    for _ in range(6):
        s = _rand_word(rng, 2, 10)
        cases.append({"args": [s], "stdout": _first_last_char(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# word_edges – first and last char of each word
# ---------------------------------------------------------------------------

def _word_edges(s: str) -> str:
    words = s.split()
    return " ".join(_first_last_char(w) for w in words if w)


def gen_word_edges(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["Hello World"], "stdout": "Ho Wd\n"},
        {"args": [""], "stdout": "\n"},
        {"args": ["a"], "stdout": "aa\n"},
    ]
    for _ in range(7):
        s = _rand_sentence(rng, rng.randint(2, 5))
        cases.append({"args": [s], "stdout": _word_edges(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# rle – run-length encoding
# ---------------------------------------------------------------------------

def _rle(s: str) -> str:
    if not s:
        return ""
    result: list[str] = []
    i = 0
    while i < len(s):
        count = 1
        while i + count < len(s) and s[i + count] == s[i]:
            count += 1
        if count > 1:
            result.append(str(count))
        result.append(s[i])
        i += count
    return "".join(result)


def gen_rle(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["AAABBC"], "stdout": "3A2BC\n"},
        {"args": ["AAAAAAAAAAAA"], "stdout": "12A\n"},
        {"args": [""], "stdout": "\n"},
        {"args": ["A"], "stdout": "A\n"},
        {"args": ["AB"], "stdout": "AB\n"},
    ]
    # Large repeat
    big = "X" * 100
    cases.append({"args": [big], "stdout": "100X\n"})
    for _ in range(4):
        chars = [rng.choice("ABCDE") for _ in range(rng.randint(3, 15))]
        s = "".join(chars)
        cases.append({"args": [s], "stdout": _rle(s) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# rle_decode
# ---------------------------------------------------------------------------

def _rle_decode(s: str) -> str:
    if not s:
        return ""
    result: list[str] = []
    i = 0
    while i < len(s):
        num = ""
        while i < len(s) and s[i].isdigit():
            num += s[i]
            i += 1
        count = int(num) if num else 1
        if i < len(s):
            result.append(s[i] * count)
            i += 1
    return "".join(result)


def gen_rle_decode(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["3A2BC"], "stdout": "AAABBC\n"},
        {"args": ["12A"], "stdout": "AAAAAAAAAAAA\n"},
        {"args": [""], "stdout": "\n"},
        {"args": ["A"], "stdout": "A\n"},
        {"args": ["100X"], "stdout": "X" * 100 + "\n"},
    ]
    for _ in range(5):
        # Generate a valid RLE string
        parts: list[str] = []
        expected: list[str] = []
        for _ in range(rng.randint(2, 5)):
            c = rng.choice("ABCDE")
            n = rng.randint(1, 8)
            if n > 1:
                parts.append(f"{n}{c}")
            else:
                parts.append(c)
            expected.append(c * n)
        rle_str = "".join(parts)
        cases.append({"args": [rle_str], "stdout": "".join(expected) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# digit_sum
# ---------------------------------------------------------------------------

def _digit_sum(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))


def gen_digit_sum(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["0"], "stdout": "0\n"},
        {"args": ["42"], "stdout": "6\n"},
        {"args": ["123"], "stdout": "6\n"},
        {"args": ["-123"], "stdout": "6\n"},
    ]
    for _ in range(6):
        n = rng.randint(0, 999999)
        cases.append({"args": [str(n)], "stdout": str(_digit_sum(n)) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# digit_root
# ---------------------------------------------------------------------------

def _digit_root(n: int) -> int:
    n = abs(n)
    while n >= 10:
        n = sum(int(d) for d in str(n))
    return n


def gen_digit_root(seed: int | None = None) -> list[dict]:
    rng = _rng(seed)
    cases = [
        {"args": ["0"], "stdout": "0\n"},
        {"args": ["9"], "stdout": "9\n"},
        {"args": ["123"], "stdout": "6\n"},
        {"args": ["9999"], "stdout": "9\n"},
        {"args": ["493193"], "stdout": str(_digit_root(493193)) + "\n"},
    ]
    for _ in range(5):
        n = rng.randint(10, 9999999)
        cases.append({"args": [str(n)], "stdout": str(_digit_root(n)) + "\n"})
    return cases


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

GENERATORS: dict[str, callable] = {
    "zigzag": gen_zigzag,
    "index_case": gen_index_case,
    "alpha_index_case": gen_alpha_index_case,
    "alt_case": gen_alt_case,
    "snake_to_camel": gen_snake_to_camel,
    "camel_to_snake": gen_camel_to_snake,
    "snake_case": gen_snake_case,
    "ping_pong": gen_ping_pong,
    "nth_remove": gen_nth_remove,
    "nth_reverse": gen_nth_reverse,
    "print_nth_char": gen_print_nth_char,
    "first_last_char": gen_first_last_char,
    "word_edges": gen_word_edges,
    "rle": gen_rle,
    "rle_decode": gen_rle_decode,
    "digit_sum": gen_digit_sum,
    "digit_root": gen_digit_root,
}
