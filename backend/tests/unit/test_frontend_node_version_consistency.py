import re
from pathlib import Path


def _normalize_node_version(raw: str) -> str:
    return raw.strip().lstrip("v").strip()


def test_frontend_dockerfile_node_version_matches_nvmrc() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    nvmrc_path = repository_root / "frontend" / ".nvmrc"
    dockerfile_path = repository_root / "frontend" / "Dockerfile"

    assert nvmrc_path.exists(), "frontend/.nvmrc must exist as the single source of truth for the Node version"
    assert dockerfile_path.exists(), "frontend/Dockerfile must exist"

    nvmrc_version = _normalize_node_version(nvmrc_path.read_text(encoding="utf-8").splitlines()[0])
    assert nvmrc_version, "frontend/.nvmrc must not be empty"

    dockerfile_text = dockerfile_path.read_text(encoding="utf-8")
    match = re.search(r"^ARG\s+NODE_VERSION=(.+)$", dockerfile_text, re.MULTILINE)
    assert match is not None, "frontend/Dockerfile must define a default NODE_VERSION via 'ARG NODE_VERSION=...'"

    dockerfile_version = _normalize_node_version(match.group(1))
    assert dockerfile_version, "Default NODE_VERSION in frontend/Dockerfile must not be empty"

    assert nvmrc_version == dockerfile_version, (
        f"NODE_VERSION default in frontend/Dockerfile ({dockerfile_version}) "
        f"must match frontend/.nvmrc ({nvmrc_version})"
    )
