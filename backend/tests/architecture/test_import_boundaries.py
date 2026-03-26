"""Architecture tests — import boundary enforcement via import-linter.

These tests verify that module boundaries defined in pyproject.toml
[tool.importlinter] contracts are respected.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.mark.architecture
def test_import_linter_contracts():
    """All import-linter contracts defined in pyproject.toml must pass."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "from importlinter.cli import lint_imports_command; lint_imports_command()"],
        capture_output=True,
        text=True,
        cwd=_BACKEND_ROOT,
    )
    assert result.returncode == 0, (
        f"import-linter found violations:\n{result.stdout}\n{result.stderr}"
    )
