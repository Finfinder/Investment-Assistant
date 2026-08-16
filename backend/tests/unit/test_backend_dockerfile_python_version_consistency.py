import re
from pathlib import Path


def _normalize_version(raw: str) -> str:
    return raw.strip().lstrip("v").strip()


def test_backend_dockerfile_python_version_matches_python_version_file() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    python_version_file_path = repository_root / "backend" / ".python-version"
    dockerfile_path = repository_root / "backend" / "Dockerfile"

    assert python_version_file_path.exists(), (
        "backend/.python-version must exist as the single source of truth for the Python version"
    )
    assert dockerfile_path.exists(), "backend/Dockerfile must exist"

    python_version_file_lines = python_version_file_path.read_text(encoding="utf-8").splitlines()
    assert python_version_file_lines, "backend/.python-version must not be empty"
    python_version_file_version = _normalize_version(python_version_file_lines[0])
    assert python_version_file_version, "backend/.python-version must not be empty"

    dockerfile_text = dockerfile_path.read_text(encoding="utf-8")
    match = re.search(r"^ARG\s+PYTHON_VERSION=(.+)$", dockerfile_text, re.MULTILINE)
    assert match is not None, "backend/Dockerfile must define a default PYTHON_VERSION via 'ARG PYTHON_VERSION=...'"

    dockerfile_version = _normalize_version(match.group(1))
    assert dockerfile_version, "Default PYTHON_VERSION in backend/Dockerfile must not be empty"

    # The Dockerfile image tag carries the variant suffix (e.g. 3.12-slim) while the
    # single source of truth (.python-version) carries only the interpreter version (e.g. 3.12).
    # The Dockerfile tag must start with the interpreter version to stay in sync.
    assert dockerfile_version.startswith(python_version_file_version), (
        f"PYTHON_VERSION default in backend/Dockerfile ({dockerfile_version}) "
        f"must start with backend/.python-version ({python_version_file_version})"
    )
