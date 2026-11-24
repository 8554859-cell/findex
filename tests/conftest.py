from pathlib import Path

import pytest


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    (tmp_path / "a.txt").write_text("python event loop", encoding="utf-8")
    (tmp_path / "b.txt").write_text("python python thread", encoding="utf-8")
    return tmp_path
