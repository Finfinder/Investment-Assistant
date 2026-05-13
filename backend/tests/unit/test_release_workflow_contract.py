from pathlib import Path


def test_release_workflow_uses_local_release_workflow_adapters() -> None:
    workflow_path = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "release.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "uses: ./.github/workflows/reusable-version-consistency.yml" in workflow_text
    assert "uses: ./.github/workflows/reusable-next-version-request.yml" in workflow_text
    assert "Finfinder/AI_Instruction/.github/workflows/reusable-version-consistency.yml@main" not in workflow_text
    assert "Finfinder/AI_Instruction/.github/workflows/reusable-next-version-request.yml@main" not in workflow_text
    assert "source-repository: ${{ github.repository }}" in workflow_text
    assert "repository-ref: ${{ github.ref }}" in workflow_text
    assert "needs: [version-consistency, next-version-request]" in workflow_text
    assert "expected-release-version: ${{ github.ref_name }}" in workflow_text
    assert "Validate next version request" not in workflow_text


def test_third_party_action_pinning_uses_repo_local_policy_bundle() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    wrapper_text = (repository_root / ".github" / "workflows" / "third-party-action-pinning.yml").read_text(
        encoding="utf-8"
    )
    reusable_text = (repository_root / ".github" / "workflows" / "reusable-third-party-action-pinning.yml").read_text(
        encoding="utf-8"
    )

    assert "uses: ./.github/workflows/reusable-third-party-action-pinning.yml" in wrapper_text
    assert "Join-Path $repositoryRoot '.github/actions-security/zizmor.yml'" in reusable_text
    assert "Policy source: repo-local mirror" in reusable_text
    assert "automation-repository:" not in reusable_text
    assert "Join-Path $env:RUNNER_TEMP 'zizmor-third-party-action-pinning.yml'" not in reusable_text
    assert (repository_root / ".github" / "actions-security" / "zizmor.yml").exists()


def test_reusable_version_consistency_uses_repo_local_validator() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    reusable_text = (repository_root / ".github" / "workflows" / "reusable-version-consistency.yml").read_text(
        encoding="utf-8"
    )

    assert reusable_text.count("uses: actions/checkout@v5") == 1
    assert "Checkout automation repository" not in reusable_text
    assert '"${{ github.workspace }}/repository/.github/scripts/validate-version-consistency.ps1"' in reusable_text
    assert '"${{ github.workspace }}/ai_instruction/scripts/validate-version-consistency.ps1"' not in reusable_text
    assert (repository_root / ".github" / "scripts" / "validate-version-consistency.ps1").exists()
