[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [switch]$Apply,

    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Resolve-Path -LiteralPath $RepoRoot
$mode = if ($Apply) { 'apply' } else { 'dry-run' }

function Write-Log {
    param([string]$Message)
    Write-Host "[prepare-release] $Message"
}

function Get-Today {
    return (Get-Date -Format 'yyyy-MM-dd')
}

function Move-UnreleasedToVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ChangelogPath,

        [Parameter(Mandatory = $true)]
        [string]$Version,

        [Parameter(Mandatory = $true)]
        [string]$Date
    )

    $content = [System.IO.File]::ReadAllText($ChangelogPath)
    $lines = $content.Split([Environment]::NewLine)

    $unreleasedStart = $null
    $unreleasedEnd = $null
    $firstVersionHeader = $null

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -eq '## [Unreleased]') {
            $unreleasedStart = $i
            continue
        }

        if ($null -ne $unreleasedStart -and $null -eq $unreleasedEnd) {
            if ($lines[$i].StartsWith('## [')) {
                $unreleasedEnd = $i
                if ($null -eq $firstVersionHeader) {
                    $firstVersionHeader = $i
                }
                break
            }
        }

        if ($null -eq $unreleasedStart -and $lines[$i].StartsWith('## [') -and $lines[$i] -ne '## [Unreleased]') {
            $firstVersionHeader = $i
        }
    }

    if ($null -eq $unreleasedStart) {
        Write-Log "No '## [Unreleased]' section found in CHANGELOG.md; nothing to move."
        return $false
    }

    if ($null -eq $unreleasedEnd) {
        $unreleasedEnd = $lines.Count
    }

    $unreleasedBody = @()
    for ($i = $unreleasedStart + 1; $i -lt $unreleasedEnd; $i++) {
        $unreleasedBody += $lines[$i]
    }

    while ($unreleasedBody.Count -gt 0 -and [string]::IsNullOrWhiteSpace($unreleasedBody[0])) {
        $unreleasedBody = @($unreleasedBody | Select-Object -Skip 1)
    }
    while ($unreleasedBody.Count -gt 0 -and [string]::IsNullOrWhiteSpace($unreleasedBody[-1])) {
        $unreleasedBody = @($unreleasedBody | Select-Object -SkipLast 1)
    }

    $newHeader = "## [$Version] - $Date"
    $newSection = @("## [Unreleased]", "", $newHeader)

    if ($unreleasedBody.Count -gt 0) {
        $newSection += ''
        $newSection += $unreleasedBody
    }

    $resultLines = @()
    $resultLines += $lines[0..($unreleasedStart - 1)]
    $resultLines += $newSection

    if ($null -ne $firstVersionHeader) {
        $resultLines += $lines[$firstVersionHeader..($lines.Count - 1)]
    }
    else {
        $resultLines += $lines[$unreleasedEnd..($lines.Count - 1)]
    }

    $updated = $resultLines -join [Environment]::NewLine
    if (-not $updated.EndsWith([Environment]::NewLine)) {
        $updated += [Environment]::NewLine
    }

    if ($Apply) {
        [System.IO.File]::WriteAllText($ChangelogPath, $updated)
        Write-Log "Moved '## [Unreleased]' content under '$newHeader' in CHANGELOG.md"
    }
    else {
        Write-Log "[dry-run] Would move '## [Unreleased]' content under '$newHeader' in CHANGELOG.md"
    }

    return $true
}

function Update-VersionTargets {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,

        [Parameter(Mandatory = $true)]
        [string]$NextVersion
    )

    $strategiesPath = Join-Path -Path $RepoRoot -ChildPath '.github/scripts/version-target-strategies.ps1'
    if (-not (Test-Path -LiteralPath $strategiesPath)) {
        throw "version-target-strategies.ps1 not found at $strategiesPath"
    }

    . $strategiesPath

    $targets = @(
        @{ Path = Join-Path -Path $RepoRoot -ChildPath 'backend/pyproject.toml'; Strategy = 'pyproject_project_version' },
        @{ Path = Join-Path -Path $RepoRoot -ChildPath 'frontend/package.json'; Strategy = 'npm_package_version' },
        @{ Path = Join-Path -Path $RepoRoot -ChildPath 'README.md'; Strategy = 'readme_badge' }
    )

    foreach ($target in $targets) {
        if (-not (Test-Path -LiteralPath $target.Path)) {
            Write-Log "Skipping missing target: $($target.Path)"
            continue
        }

        $content = [System.IO.File]::ReadAllText($target.Path)
        $current = Get-TargetVersionFromContent -Content $content -Strategy $target.Strategy

        if ($current -eq $NextVersion) {
            Write-Log "Already at $NextVersion : $($target.Path)"
            continue
        }

        $result = Update-TargetContentByStrategy -Content $content -Strategy $target.Strategy -NextVersion $NextVersion

        if (-not $result.IsMatch) {
            Write-Log "WARN: pattern not matched for $($target.Path); skipping."
            continue
        }

        if ($Apply) {
            [System.IO.File]::WriteAllText($target.Path, $result.Content)
            Write-Log "Updated $($target.Path) -> $NextVersion (was $current)"
        }
        else {
            Write-Log "[dry-run] Would update $($target.Path) -> $NextVersion (was $current)"
        }
    }
}

$changelogPath = Join-Path -Path $repoRoot -ChildPath 'CHANGELOG.md'
if (-not (Test-Path -LiteralPath $changelogPath)) {
    throw "CHANGELOG.md not found at $changelogPath"
}

Write-Log "Mode: $mode"
Write-Log "Target version: $Version"

Move-UnreleasedToVersion -ChangelogPath $changelogPath -Version $Version -Date (Get-Today)
Update-VersionTargets -RepoRoot $repoRoot -NextVersion $Version

Write-Log "Done. Remember to commit the changes and create tag v$Version."
