[CmdletBinding()]
param(
    [string]$RepositoryUrl = "https://github.com/qianzhu18/Muku.git",
    [string]$Branch = $(if ($env:MUKU_REPO_BRANCH) { $env:MUKU_REPO_BRANCH } else { "main" })
)

$ErrorActionPreference = "Stop"
$temporaryRoot = $null

function Resolve-Python {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return @($pythonCommand.Source, "-3")
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return @($pythonCommand.Source)
    }

    throw "Muku installer requires Python 3.10 or newer. Install Python, then rerun this command."
}

try {
    $scriptPath = $MyInvocation.MyCommand.Path
    $candidateRoot = if ($scriptPath) {
        Split-Path -Parent (Split-Path -Parent $scriptPath)
    }
    if ($candidateRoot -and (Test-Path (Join-Path $candidateRoot "pyproject.toml"))) {
        $repositoryRoot = $candidateRoot
    } else {
        $temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("muku-install-" + [guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
        $archivePath = Join-Path $temporaryRoot "muku.zip"
        $archiveBaseUrl = $RepositoryUrl -replace "\.git$", ""
        $archiveUrl = "{0}/archive/refs/heads/{1}.zip" -f $archiveBaseUrl, $Branch
        Invoke-WebRequest -Uri $archiveUrl -OutFile $archivePath
        Expand-Archive -Path $archivePath -DestinationPath $temporaryRoot
        $repositoryRoot = (Get-ChildItem -Path $temporaryRoot -Directory | Select-Object -First 1).FullName
    }

    $python = Resolve-Python
    $pythonExecutable = $python[0]
    $pythonOptions = if ($python.Length -gt 1) { @($python[1]) } else { @() }
    & $pythonExecutable @pythonOptions -m pip install --user --upgrade $repositoryRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Muku CLI installation failed."
    }

    $codexRoot = if ($env:MUKU_CODEX_HOME) {
        $env:MUKU_CODEX_HOME
    } elseif ($env:CODEX_HOME) {
        $env:CODEX_HOME
    } else {
        Join-Path $env:USERPROFILE ".codex"
    }
    $skillDestination = Join-Path $codexRoot "skills\muku-video-to-md"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $skillDestination) | Out-Null
    if (Test-Path $skillDestination) {
        Remove-Item -Recurse -Force $skillDestination
    }
    Copy-Item -Recurse (Join-Path $repositoryRoot "skills\muku-video-to-md") $skillDestination

    $mukuCommand = Get-Command muku -ErrorAction SilentlyContinue
    if ($mukuCommand) {
        & $mukuCommand.Source --version
    } else {
        & $pythonExecutable @pythonOptions -m webui.cli --version
    }
    Write-Host "Installed Muku CLI and muku-video-to-md Skill."
    Write-Host "Next step: muku quickstart"
} finally {
    if ($temporaryRoot -and (Test-Path $temporaryRoot)) {
        Remove-Item -Recurse -Force $temporaryRoot
    }
}
