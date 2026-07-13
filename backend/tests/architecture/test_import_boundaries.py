"""Architecture tests — import boundary enforcement via import-linter.

These tests verify that module boundaries defined in pyproject.toml
[tool.importlinter] contracts are respected and that every domain module
under app/modules is registered in the independence contract, so that
future modules cannot silently bypass the boundary (see issue #194 / #120).
"""

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

# tests/architecture is three levels below the backend root: tests/ -> backend/ -> repo root.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _BACKEND_ROOT / "pyproject.toml"
_MODULES_ROOT = _BACKEND_ROOT / "app" / "modules"

# Directory names that are never domain modules and must be ignored when
# auto-discovering modules under app/modules (files are already filtered by is_dir()).
_IGNORED_DIR_NAMES = {"__pycache__"}


def _run_lint_imports() -> int:
    """Run import-linter contracts and return the process exit code."""
    result = subprocess.run(
        [sys.executable, "-c", "from importlinter.cli import lint_imports_command; lint_imports_command()"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_BACKEND_ROOT),
    )
    return result.returncode


def _independence_contract_modules() -> list[str]:
    """Return the module list declared in the `independence` contract."""
    with _PYPROJECT.open("rb") as handle:
        config = tomllib.load(handle)
    contracts = config.get("tool", {}).get("importlinter", {}).get("contracts", [])
    for contract in contracts:
        if contract.get("type") == "independence":
            return list(contract.get("modules", []))
    return []


def _discovered_domain_modules() -> list[str]:
    """Discover domain module packages directly under app/modules."""
    discovered = []
    if not _MODULES_ROOT.is_dir():
        return discovered
    for entry in sorted(_MODULES_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_") or entry.name in _IGNORED_DIR_NAMES:
            continue
        discovered.append(f"app.modules.{entry.name}")
    return discovered


@pytest.mark.architecture
def test_import_linter_contracts():
    """All import-linter contracts defined in pyproject.toml must pass."""
    assert _run_lint_imports() == 0, "import-linter found violations"


@pytest.mark.architecture
def test_all_domain_modules_registered_in_contract():
    """Every domain module under app/modules must be listed in the independence contract.

    This guards against the silent regression from issue #120, where a new
    domain module outside the contract list was not protected by the boundary.
    """
    registered = set(_independence_contract_modules())
    discovered = _discovered_domain_modules()

    assert discovered, "Expected at least one domain module under app/modules"
    unregistered = sorted(module for module in discovered if module not in registered)
    assert not unregistered, (
        "Domain modules not registered in the import-linter independence contract: "
        f"{unregistered}. Add them to the `modules` list of the independence contract "
        "in backend/pyproject.toml."
    )


@pytest.mark.architecture
def test_registered_module_violation_detected():
    """A cross-module import inside a registered domain module is detected.

    Proves the independence contract actually catches violations in modules that
    are registered in the contract, closing the #120-class gap for future modules.
    The probe module is temporarily registered in pyproject.toml so the contract
    evaluates it, then the original configuration is restored.
    """
    probe_dir = _MODULES_ROOT / "_contract_probe"
    probe_file = probe_dir / "__init__.py"
    probe_dir.mkdir(exist_ok=True)
    original_text = _PYPROJECT.read_text(encoding="utf-8")
    try:
        probe_file.write_text(
            "from app.modules.technical_analysis import signal_rating\n",
            encoding="utf-8",
        )
        # Register the probe module so the independence contract evaluates it.
        probe_module = "app.modules._contract_probe"
        if probe_module not in _independence_contract_modules():
            updated_text = original_text.replace(
                '    "app.modules.strategy_generator",\n',
                '    "app.modules.strategy_generator",\n    "app.modules._contract_probe",\n',
            )
            _PYPROJECT.write_text(updated_text, encoding="utf-8")
        assert _run_lint_imports() != 0, "Expected import-linter to detect the cross-module import in the probe module"
    finally:
        if probe_file.exists():
            probe_file.unlink()
        if probe_dir.exists():
            probe_dir.rmdir()
        # Always restore the original pyproject.toml configuration.
        _PYPROJECT.write_text(original_text, encoding="utf-8")
