"""String-case generators (re-exported from handwritten for backwards compat)."""
from piscine_forge.generators.handwritten import (
    gen_zigzag,
    gen_index_case,
    gen_alpha_index_case,
    gen_alt_case,
    gen_snake_to_camel,
    gen_camel_to_snake,
    gen_snake_case,
    GENERATORS,
)

__all__ = [
    "gen_zigzag",
    "gen_index_case",
    "gen_alpha_index_case",
    "gen_alt_case",
    "gen_snake_to_camel",
    "gen_camel_to_snake",
    "gen_snake_case",
    "GENERATORS",
]
