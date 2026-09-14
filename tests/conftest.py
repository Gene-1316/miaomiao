"""Use fresh task-owned temp directories; avoid a locked global pytest cache."""
from pathlib import Path
import tempfile
import pytest


@pytest.fixture
def tmp_path():
    root = Path(__file__).resolve().parents[1] / "artifacts" / "test_runs"
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="case-", dir=root) as directory:
        path = Path(directory).resolve()
        assert path.is_relative_to(root.resolve())
        yield path
