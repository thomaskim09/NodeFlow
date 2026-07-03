param(
    [ValidateSet("auto", "windows", "macos")]
    [string]$Target = "auto"
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$PyInstaller = Join-Path $VenvDir "Scripts\pyinstaller.exe"
$PythonCmd = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment in $VenvDir"
    & $PythonCmd -m venv $VenvDir
}

Write-Host "Installing packaging dependencies"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "$RootDir[dev]"

if ($Target -eq "auto") {
    $Target = "windows"
}

switch ($Target) {
    "windows" {
        $SpecFile = Join-Path $RootDir "packaging\windows.spec"
    }
    "macos" {
        throw "macOS bundles must be built on macOS."
    }
}

Write-Host "Packaging NodeFlow for $Target"
Set-Location $RootDir
& $VenvPython (Join-Path $RootDir "scripts\build_app_icons.py") $Target
& $PyInstaller $SpecFile --clean
