import tomllib
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version


def test_python_version_file_is_single_source_of_truth() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    version_file = repository_root / "backend" / ".python-version"
    pyproject_path = repository_root / "backend" / "pyproject.toml"

    assert version_file.exists(), "backend/.python-version must exist as the single source of truth"
    raw = version_file.read_text(encoding="utf-8").strip()
    assert raw, "backend/.python-version must not be empty"

    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    requires_python = pyproject["project"]["requires-python"]

    try:
        specifier = SpecifierSet(requires_python)
    except InvalidSpecifier as exc:
        raise AssertionError(f"requires-python is not a valid specifier: {requires_python}") from exc

    assert Version(raw) in specifier, (
        f"backend/.python-version ({raw}) must satisfy requires-python ({requires_python})"
    )
