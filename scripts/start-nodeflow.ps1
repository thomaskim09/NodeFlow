$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$PythonCmd = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$StampFile = Join-Path $VenvDir ".nodeflow-runtime-installed"
$ForceInstall = $false

foreach ($Arg in $args) {
    switch ($Arg) {
        "--reinstall" {
            $ForceInstall = $true
        }
        "--help" {
            Write-Host "Usage: .\scripts\start-nodeflow.ps1 [--reinstall]"
            Write-Host ""
            Write-Host "Starts NodeFlow with the local .venv Python."
            Write-Host ""
            Write-Host "Options:"
            Write-Host "  --reinstall   Reinstall runtime dependencies before launch."
            exit 0
        }
        "-h" {
            Write-Host "Usage: .\scripts\start-nodeflow.ps1 [--reinstall]"
            exit 0
        }
        default {
            throw "Unknown option: $Arg"
        }
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment in $VenvDir"
    & $PythonCmd -m venv $VenvDir
    $ForceInstall = $true
}

if ($ForceInstall -or -not (Test-Path $StampFile)) {
    Write-Host "Installing NodeFlow runtime dependencies"
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -e $RootDir
    Set-Content -Path $StampFile -Value "installed" -NoNewline
}

Write-Host "Starting NodeFlow"
Set-Location $RootDir
& $VenvPython main.py
