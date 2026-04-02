$service = Get-Service | Where-Object {
    $_.Name -match "ScreenConnect|ConnectWise|Control"
}

if ($service) {
    Write-Output "Detected"
    exit 0
}

$paths = @(
    "C:\Program Files\ScreenConnect Client*",
    "C:\Program Files (x86)\ScreenConnect Client*",
    "C:\Program Files\ConnectWise*",
    "C:\Program Files (x86)\ConnectWise*"
)

foreach ($path in $paths) {
    if (Test-Path $path) {
        Write-Output "Detected"
        exit 0
    }
}

exit 1