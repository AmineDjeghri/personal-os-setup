#requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoFolderName = 'personal-os-setup'

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory=$true)][string]$Command,
        [string[]]$Arguments
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command '$Command' failed with exit code $LASTEXITCODE."
    }
}

function Update-SessionPath {
    $registered = @(
        [System.Environment]::GetEnvironmentVariable('Path', 'Machine'),
        [System.Environment]::GetEnvironmentVariable('Path', 'User')
    ) | Where-Object { $_ }
    $env:Path = (@($env:Path) + $registered) -join ';'
}

function Ensure-Winget {
    $command = Get-Command winget -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return $null
}

function Ensure-Git {
    $command = Get-Command git -ErrorAction SilentlyContinue
    if (-not $command) {
        $wingetPath = Ensure-Winget
        if (-not $wingetPath) {
            throw "Git is required. Install Git for Windows and re-run this script."
        }
        Write-Host "Installing Git for Windows..." -ForegroundColor Yellow
        Invoke-CheckedCommand -Command $wingetPath -Arguments @(
            'install', '-e', '--id', 'Git.Git',
            '--accept-source-agreements', '--accept-package-agreements'
        ) | Out-Host
        Update-SessionPath
        $command = Get-Command git -ErrorAction SilentlyContinue
    }
    if (-not $command) {
        throw "Git was not found after installation. Restart PowerShell and re-run."
    }
    return $command.Source
}

function Get-CheckoutRoot {
    param([string]$GitPath)
    # Outside a checkout, rev-parse is an expected failed probe.
    try {
        $inside = & $GitPath rev-parse --is-inside-work-tree 2>$null
        if ($LASTEXITCODE -ne 0 -or $inside -ne 'true') { return $null }
    } catch {
        return $null
    }
    Invoke-CheckedCommand -Command $GitPath -Arguments @('rev-parse', '--show-toplevel')
}

function Resolve-Make {
    foreach ($name in @('make', 'mingw32-make', 'gmake')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    $fallback = 'C:\Program Files (x86)\GnuWin32\bin\make.exe'
    if (Test-Path $fallback) { return $fallback }
    return $null
}

function Add-ToPathIfMissing {
    param(
        [Parameter(Mandatory=$true)][string]$Dir,
        [switch]$Persist
    )
    if (($env:Path -split ';') -notcontains $Dir) {
        $env:Path = "$Dir;" + $env:Path
    }
    if ($Persist) {
        $userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
        if (($userPath -split ';') -notcontains $Dir) {
            $newPath = if ($userPath) { "$Dir;$userPath" } else { $Dir }
            [System.Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        }
    }
}

function Ensure-Bash {
    param([string]$GitPath)
    $gitDirectory = Split-Path -Parent $GitPath
    if ($gitDirectory) {
        $gitRoot = Split-Path -Parent $gitDirectory
        $gitBin = Join-Path $gitRoot 'bin'
        if (Test-Path (Join-Path $gitBin 'bash.exe')) {
            # Prefer Git Bash to the Windows WSL bash shim.
            $otherPaths = ($env:Path -split ';') | Where-Object { $_ -ne $gitBin }
            $env:Path = "$gitBin;" + ($otherPaths -join ';')
            return
        }
    }
    if (-not (Get-Command bash -ErrorAction SilentlyContinue)) {
        throw "Bash is required by Make. Install Git for Windows and re-run."
    }
}

function Ensure-Make {
    $makePath = Resolve-Make
    if ($makePath) { return $makePath }
    $wingetPath = Ensure-Winget
    if (-not $wingetPath) {
        throw "GNU Make is required. Install it with winget, Chocolatey or Scoop and re-run."
    }
    Write-Host "Installing GNU Make..." -ForegroundColor Yellow
    Invoke-CheckedCommand -Command $wingetPath -Arguments @(
        'install', '-e', '--id', 'GnuWin32.Make',
        '--accept-source-agreements', '--accept-package-agreements'
    ) | Out-Host
    Update-SessionPath
    $makePath = Resolve-Make
    if (-not $makePath) {
        throw "GNU Make was not found after installation. Restart PowerShell and re-run."
    }
    Add-ToPathIfMissing -Dir (Split-Path -Parent $makePath) -Persist
    return $makePath
}

function Invoke-Make {
    param([Parameter(Mandatory=$true)][string[]]$MakeArguments)
    $makePath = Resolve-Make
    if (-not $makePath) { throw "GNU Make is unavailable." }
    $makefile = Join-Path $RepoRoot 'Makefile'
    Invoke-CheckedCommand -Command $makePath -Arguments (
        @('--no-print-directory', '-f', $makefile) + $MakeArguments
    )
}

function Ensure-Chezmoi {
    if (Get-Command chezmoi -ErrorAction SilentlyContinue) { return }
    $wingetPath = Ensure-Winget
    if ($wingetPath) {
        try {
            Invoke-CheckedCommand -Command $wingetPath -Arguments @(
                'install', '-e', '--id', 'twpayne.chezmoi',
                '--accept-source-agreements', '--accept-package-agreements'
            ) | Out-Host
            Update-SessionPath
            if (Get-Command chezmoi -ErrorAction SilentlyContinue) { return }
        } catch {
            Write-Host "Optional chezmoi installation failed: $_" -ForegroundColor DarkYellow
        }
    }
    Write-Host "Install chezmoi manually if you need dotfiles deployment." -ForegroundColor DarkYellow
}

function Install-CommandShim {
    $exe = Join-Path $RepoRoot '.venv\Scripts\personal-os-setup.exe'
    if (-not (Test-Path $exe)) { return }
    $shimDir = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
    if (Test-Path $shimDir) {
        $shimPath = Join-Path $shimDir 'personal-os-setup.cmd'
        Set-Content -Path $shimPath -Value @('@echo off', ('"{0}" %*' -f $exe)) -Encoding ASCII
        Write-Host "Linked personal-os-setup -> $shimPath" -ForegroundColor Green
    } else {
        Add-ToPathIfMissing -Dir (Join-Path $RepoRoot '.venv\Scripts') -Persist
    }
}

# Define every helper before bootstrapping a machine that may not have Git yet.
$git = Ensure-Git
$RepoRoot = $null
$checkout = Get-CheckoutRoot -GitPath $git
if ($checkout -and (Split-Path -Leaf $checkout) -eq $RepoFolderName) {
    $RepoRoot = $checkout
}
if (-not $RepoRoot) {
    $destination = Join-Path $env:USERPROFILE '.personal-os-setup'
    if (Test-Path $destination) {
        Set-Location $destination
        $checkout = Get-CheckoutRoot -GitPath $git
        if (-not $checkout -or
            [System.IO.Path]::GetFullPath($checkout) -ne [System.IO.Path]::GetFullPath($destination)) {
            throw "Folder exists but is not the expected Git checkout: $destination"
        }
    } else {
        Invoke-CheckedCommand -Command $git -Arguments @(
            'clone', 'https://github.com/AmineDjeghri/personal-os-setup.git', $destination
        ) | Out-Host
    }
    $RepoRoot = $destination
}

Set-Location $RepoRoot
Write-Host "Pulling (fast-forward only)..." -ForegroundColor Yellow
Invoke-CheckedCommand -Command $git -Arguments @('pull', '--ff-only') | Out-Host
Ensure-Bash -GitPath $git
$null = Ensure-Make
Ensure-Chezmoi

Write-Host "Running: make install-prod" -ForegroundColor Yellow
Invoke-Make -MakeArguments @('install-prod')
Install-CommandShim
Write-Host "Running: make run" -ForegroundColor Yellow
Invoke-Make -MakeArguments @('run')
Write-Host "Done" -ForegroundColor Green
