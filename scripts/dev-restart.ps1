<#
.SYNOPSIS
    Restart the dev backend on a clean process so browser verification never
    runs against stale code.

.DESCRIPTION
    The dev server can silently keep serving an old build after source changes
    (a lingering uvicorn process). That has already produced false "regressions"
    in playtest synthesis. This helper makes the fresh-process guard from the
    multi-phase plan's "Standing verification protocol" a single command:

        1. Find and kill any process listening on the dev port.
        2. Start a fresh backend (python -m dodgeball_sim).
        3. Wait until the new process is actually listening.
        4. Print the OLD PID(s) it killed and the NEW PID, so you can confirm
           they differ before trusting any browser screenshot.

    Exit code is 0 on success, non-zero if the server never came up.

.PARAMETER Port
    Dev backend port. Defaults to 8000 (DEFAULT_BACKEND_PORT in web_cli.py).

.PARAMETER TimeoutSeconds
    How long to wait for the fresh process to start listening. Default 30.

.EXAMPLE
    pwsh scripts/dev-restart.ps1
    pwsh scripts/dev-restart.ps1 -Port 8000
#>
[CmdletBinding()]
param(
    [int]$Port = 8000,
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'

function Get-PortPids {
    param([int]$Port)
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        return @($conns | Select-Object -ExpandProperty OwningProcess -Unique)
    } catch {
        return @()
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "== dev-restart: port $Port ==" -ForegroundColor Cyan

# 1. Kill whatever is on the port.
$oldPids = Get-PortPids -Port $Port
if ($oldPids.Count -gt 0) {
    foreach ($procId in $oldPids) {
        Write-Host ("Stopping stale PID {0} on port {1}" -f $procId, $Port) -ForegroundColor Yellow
        try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch {
            Write-Warning ("Could not stop PID {0}: {1}" -f $procId, $_.Exception.Message)
        }
    }
    # Give the OS a moment to release the socket.
    $waited = 0
    while ((Get-PortPids -Port $Port).Count -gt 0 -and $waited -lt 10) {
        Start-Sleep -Milliseconds 300
        $waited++
    }
} else {
    Write-Host "No existing listener on port $Port." -ForegroundColor DarkGray
}

# 2. Start a fresh backend, detached, in the repo root.
Write-Host "Starting fresh backend (python -m dodgeball_sim)..." -ForegroundColor Cyan
$proc = Start-Process -FilePath 'python' -ArgumentList '-m', 'dodgeball_sim' `
    -WorkingDirectory $repoRoot -PassThru

# 3. Wait until the NEW process is listening on the port.
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$newPid = $null
while ((Get-Date) -lt $deadline) {
    $listening = Get-PortPids -Port $Port
    if ($listening.Count -gt 0) {
        $newPid = $listening[0]
        break
    }
    if ($proc.HasExited) {
        Write-Error ("Backend process exited early (exit code {0}) before binding port {1}." -f $proc.ExitCode, $Port)
        exit 1
    }
    Start-Sleep -Milliseconds 400
}

if ($null -eq $newPid) {
    Write-Error ("Backend did not start listening on port {0} within {1}s." -f $Port, $TimeoutSeconds)
    exit 1
}

# 4. Report so the caller can confirm freshness.
$oldList = if ($oldPids.Count -gt 0) { ($oldPids -join ', ') } else { '(none)' }
Write-Host ""
Write-Host ("Old PID(s): {0}" -f $oldList) -ForegroundColor Magenta
Write-Host ("New PID   : {0}" -f $newPid) -ForegroundColor Green
if ($oldPids -contains $newPid) {
    Write-Warning "New PID matches an old PID -- the restart may not have taken. Investigate."
    exit 1
}
Write-Host ("Fresh backend confirmed on http://127.0.0.1:{0} (PID {1})." -f $Port, $newPid) -ForegroundColor Green
exit 0
