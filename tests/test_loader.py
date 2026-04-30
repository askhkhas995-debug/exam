from pathlib import Path
from piscine_forge.loader import Repository


def test_repository_loads():
    repo = Repository(Path.cwd())
    assert isinstance(repo.subjects(), dict)
    assert isinstance(repo.pools(), dict)
