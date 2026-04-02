# Remove-DattoRMM.ps1
# Run as Administrator / SYSTEM
# Logs to C:\ProgramData\RMMTransition\Remove-DattoRMM.log

$ErrorActionPreference = "Continue"

$LogDir = "C:\ProgramData\RMMTransition"
$LogFile = Join-Path $LogDir "Remove-DattoRMM.log"

if (-not (Test-Path $LogDir)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

Start-Transcript -Path $LogFile -Append

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

Write-Log "==== Starting Datto removal script ===="

# Common keywords seen in app/service/task names
$keywords = @(
    "Datto",
    "Datto RMM",
    "Advanced Monitoring Agent",
    "AEMAgent",
    "CentraStage"
)

# 1) Stop matching services
Write-Log "Checking services..."
$services = Get-Service | Where-Object {
    $svcName = $_.Name
    $dispName = $_.DisplayName
    $keywords | ForEach-Object {
        if ($svcName -like "*$_*" -or $dispName -like "*$_*") { $true }
    }
}

if ($services) {
    foreach ($svc in $services) {
        try {
            Write-Log "Stopping service: $($svc.Name) / $($svc.DisplayName)"
            Stop-Service -Name $svc.Name -Force -ErrorAction Continue
        } catch {
            Write-Log "Failed to stop service $($svc.Name): $($_.Exception.Message)"
        }
    }
} else {
    Write-Log "No matching Datto-related services found."
}

# 2) Disable / remove matching scheduled tasks
Write-Log "Checking scheduled tasks..."
try {
    $tasks = Get-ScheduledTask | Where-Object {
        $taskName = $_.TaskName
        $taskPath = $_.TaskPath
        $keywords | ForEach-Object {
            if ($taskName -like "*$_*" -or $taskPath -like "*$_*") { $true }
        }
    }

    if ($tasks) {
        foreach ($task in $tasks) {
            try {
                Write-Log "Disabling scheduled task: $($task.TaskPath)$($task.TaskName)"
                Disable-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction Continue | Out-Null
            } catch {
                Write-Log "Failed to disable task $($task.TaskName): $($_.Exception.Message)"
            }
        }
    } else {
        Write-Log "No matching scheduled tasks found."
    }
} catch {
    Write-Log "Scheduled task enumeration failed: $($_.Exception.Message)"
}

# 3) Search uninstall registry keys
Write-Log "Searching uninstall registry keys..."
$uninstallPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$apps = foreach ($path in $uninstallPaths) {
    Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object {
        $displayName = $_.DisplayName
        if ([string]::IsNullOrWhiteSpace($displayName)) { return $false }
        $keywords | ForEach-Object {
            if ($displayName -like "*$_*") { $true }
        }
    }
}

if ($apps) {
    foreach ($app in $apps | Sort-Object DisplayName -Unique) {
        Write-Log "Found installed app: $($app.DisplayName)"
        $uninstallString = $app.UninstallString
        $quietUninstallString = $app.QuietUninstallString

        try {
            if (-not [string]::IsNullOrWhiteSpace($quietUninstallString)) {
                Write-Log "Running QuietUninstallString for $($app.DisplayName): $quietUninstallString"
                Start-Process -FilePath "cmd.exe" -ArgumentList "/c $quietUninstallString" -Wait -WindowStyle Hidden
            }
            elseif (-not [string]::IsNullOrWhiteSpace($uninstallString)) {
                Write-Log "Running UninstallString for $($app.DisplayName): $uninstallString"

                if ($uninstallString -match "msiexec") {
                    $args = $uninstallString -replace '(?i)^.*?msiexec(\.exe)?\s*', ''
                    if ($args -notmatch '(/qn|/quiet)') {
                        $args = "$args /qn /norestart"
                    }
                    Start-Process -FilePath "msiexec.exe" -ArgumentList $args -Wait -WindowStyle Hidden
                } else {
                    Start-Process -FilePath "cmd.exe" -ArgumentList "/c $uninstallString" -Wait -WindowStyle Hidden
                }
            } else {
                Write-Log "No uninstall string found for $($app.DisplayName)"
            }
        } catch {
            Write-Log "Uninstall attempt failed for $($app.DisplayName): $($_.Exception.Message)"
        }
    }
} else {
    Write-Log "No matching installed Datto-related apps found in uninstall registry."
}

# 4) Kill lingering processes
Write-Log "Checking lingering processes..."
$processes = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $procName = $_.ProcessName
    $keywords | ForEach-Object {
        if ($procName -like "*$_*") { $true }
    }
}

if ($processes) {
    foreach ($proc in $processes) {
        try {
            Write-Log "Stopping process: $($proc.ProcessName) (PID $($proc.Id))"
            Stop-Process -Id $proc.Id -Force -ErrorAction Continue
        } catch {
            Write-Log "Failed to stop process $($proc.ProcessName): $($_.Exception.Message)"
        }
    }
} else {
    Write-Log "No lingering Datto-related processes found."
}

# 5) Remove common leftover folders if they exist
Write-Log "Checking common leftover folders..."
$pathsToRemove = @(
    "C:\Program Files\Datto",
    "C:\Program Files (x86)\Datto",
    "C:\Program Files\CentraStage",
    "C:\Program Files (x86)\CentraStage",
    "C:\ProgramData\Datto",
    "C:\ProgramData\CentraStage"
)

foreach ($path in $pathsToRemove) {
    if (Test-Path $path) {
        try {
            Write-Log "Removing folder: $path"
            Remove-Item -Path $path -Recurse -Force -ErrorAction Continue
        } catch {
            Write-Log "Failed to remove folder ${path}: $($_.Exception.Message)"
        }
    }
}

# 6) Final status summary
Write-Log "Final matching service check..."
$remainingServices = Get-Service | Where-Object {
    $svcName = $_.Name
    $dispName = $_.DisplayName
    $keywords | ForEach-Object {
        if ($svcName -like "*$_*" -or $dispName -like "*$_*") { $true }
    }
}

Write-Log "Final matching app check..."
$remainingApps = foreach ($path in $uninstallPaths) {
    Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object {
        $displayName = $_.DisplayName
        if ([string]::IsNullOrWhiteSpace($displayName)) { return $false }
        $keywords | ForEach-Object {
            if ($displayName -like "*$_*") { $true }
        }
    }
}

if (-not $remainingServices -and -not $remainingApps) {
    Write-Log "Datto removal appears successful."
    $exitCode = 0
} else {
    if ($remainingServices) {
        Write-Log "Remaining services detected:"
        $remainingServices | ForEach-Object { Write-Log " - $($_.Name) / $($_.DisplayName)" }
    }
    if ($remainingApps) {
        Write-Log "Remaining installed apps detected:"
        $remainingApps | Sort-Object DisplayName -Unique | ForEach-Object { Write-Log " - $($_.DisplayName)" }
    }
    Write-Log "Datto removal incomplete. Manual review may be required."
    $exitCode = 1
}

Write-Log "==== Datto removal script complete. ExitCode=$exitCode ===="
Stop-Transcript
exit $exitCode