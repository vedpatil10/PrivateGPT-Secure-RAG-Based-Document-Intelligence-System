param(
    [switch]$ReuseVenv
)

$ErrorActionPreference = "Stop"

function Get-UsablePython {
    $candidates = @()

    $commonRoots = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles\Python",
        "$env:ProgramFiles(x86)\Python"
    )

    foreach ($root in $commonRoots) {
        if (Test-Path $root) {
            $candidates += Get-ChildItem -Path $root -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -notlike "*WindowsApps*" } |
                Sort-Object FullName -Descending |
                Select-Object -ExpandProperty FullName
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd -and $pythonCmd.Source -notlike "*WindowsApps*") {
        $candidates = @($pythonCmd.Source) + $candidates
    }

    $uniqueCandidates = $candidates | Select-Object -Unique
    foreach ($candidate in $uniqueCandidates) {
        try {
            & $candidate --version | Out-Null
            return $candidate
        } catch {
            continue
        }
    }

    throw @"
No usable Python interpreter was found.

Why this happens:
- `python.exe` is often a Windows Store shim under WindowsApps.
- `py.exe` may point at a protected Store install that this shell cannot launch.

Recommended fix:
1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
2. Enable 'Add python.exe to PATH' during install
3. Turn off the App Execution Alias entries for python/python3 in Windows Settings
4. Re-run: .\scripts\verify.ps1
"@
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Get-UsablePython
$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not $ReuseVenv -or -not (Test-Path $venvPython)) {
    & $pythonExe -m venv $venvPath
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $repoRoot "requirements-ci.txt")
& $venvPython -m pytest
