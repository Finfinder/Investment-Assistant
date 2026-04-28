from pathlib import Path


def test_release_workflow_uses_shared_next_version_request_adapter() -> None:
    workflow_path = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "release.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "reusable-version-consistency.yml@main" in workflow_text
    assert "reusable-next-version-request.yml@main" in workflow_text
    assert "source-repository: ${{ github.repository }}" in workflow_text
    assert "repository-ref: ${{ github.ref }}" in workflow_text
    assert "needs: [version-consistency, next-version-request]" in workflow_text
    assert "expected-release-version: ${{ github.ref_name }}" in workflow_text
    assert "Validate next version request" not in workflow_text
