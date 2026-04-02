$ErrorActionPreference = "SilentlyContinue"

$products = Get-WmiObject Win32_Product |
    Where-Object { $_.Name -match "ConnectWise|ScreenConnect|Control" }

foreach ($product in $products) {
    $product.Uninstall() | Out-Null
}

$services = Get-Service | Where-Object {
    $_.Name -match "ScreenConnect|ConnectWise|Control"
}

if ($services) {
    exit 1
}

exit 0