param(
    [string]$InstallerPath = "C:\Windows\Temp\ConnectWiseControl.ClientSetup.msi",
    [string]$LogPath = "C:\Windows\Temp\connectwise_install.log"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

try {
    Write-Log "Starting ConnectWise install check."

    $existing = Get-WmiObject Win32_Product |
        Where-Object { $_.Name -match "ConnectWise|ScreenConnect|Control" }

    if ($existing) {
        Write-Log "ConnectWise-related product already detected: $($existing.Name)"
        exit 0
    }

    if (-not (Test-Path $InstallerPath)) {
        Write-Log "Installer not found at $InstallerPath"
        throw "Installer not found."
    }

    Write-Log "Installer found. Launching msiexec."

    $arguments = @(
        "/i"
        "`"$InstallerPath`""
        "/qn"
        "/norestart"
        "/L*v"
        "`"$LogPath`""
    )

    $process = Start-Process -FilePath "msiexec.exe" -ArgumentList $arguments -Wait -PassThru

    Write-Log "msiexec exit code: $($process.ExitCode)"

    if ($process.ExitCode -ne 0) {
        throw "Install failed with exit code $($process.ExitCode)"
    }

    Start-Sleep -Seconds 10

    $service = Get-Service | Where-Object {
        $_.Name -match "ScreenConnect|ConnectWise|Control"
    }

    if ($service) {
        Write-Log "ConnectWise-related service detected: $($service.Name)"
        exit 0
    }

    Write-Log "Install completed but no expected service found."
    throw "Post-install validation failed."
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    exit 1
}