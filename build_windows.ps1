# livan Windows one-click build script
# Usage: .\build_windows.ps1
# Output: dist\livan\  (zip this folder to distribute)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root "my_ai_env\Scripts\python.exe"
$VenvPip = Join-Path $Root "my_ai_env\Scripts\pip.exe"
$DistDir = Join-Path $Root "dist\livan"

Write-Host "==> Checking venv..." -ForegroundColor Cyan
if (-not (Test-Path $VenvPython)) {
    Write-Error "venv not found: $VenvPython"
}

Write-Host "==> Installing/updating PyInstaller..." -ForegroundColor Cyan
& $VenvPip install -U pyinstaller

Write-Host "==> Building (may take several minutes)..." -ForegroundColor Cyan
& $VenvPython -m PyInstaller --noconfirm --clean (Join-Path $Root "OpenManus.spec")
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed, exit code: $LASTEXITCODE"
}

if (-not (Test-Path $DistDir)) {
    Write-Error "dist folder not found: $DistDir"
}

Write-Host "==> Copying runtime assets next to exe..." -ForegroundColor Cyan

# config must sit beside the exe
$configSrc = Join-Path $Root "config"
$configDst = Join-Path $DistDir "config"
if (Test-Path $configDst) {
    Remove-Item $configDst -Recurse -Force
}
Copy-Item $configSrc $configDst -Recurse -Force

# optional knowledge folder
$knowledgeSrc = Join-Path $Root "knowledge"
if (Test-Path $knowledgeSrc) {
    $knowledgeDst = Join-Path $DistDir "knowledge"
    if (Test-Path $knowledgeDst) {
        Remove-Item $knowledgeDst -Recurse -Force
    }
    Copy-Item $knowledgeSrc $knowledgeDst -Recurse -Force
}

# browser_use 静态资源（防止 collect_data_files 遗漏 buildDomTree.js）
$buJs = Join-Path $Root "my_ai_env\Lib\site-packages\browser_use\dom\buildDomTree.js"
$buDstDir = Join-Path $DistDir "_internal\browser_use\dom"
if (Test-Path $buJs) {
    New-Item -ItemType Directory -Force -Path $buDstDir | Out-Null
    Copy-Item $buJs (Join-Path $buDstDir "buildDomTree.js") -Force
}

# workspace + logs
New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "workspace") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "logs") | Out-Null

# copy Chinese usage notes (separate UTF-8 file, avoid here-string encoding issues)
$readmeSrc = Join-Path $Root "packaging\README_DIST.txt"
$readmeDst = Join-Path $DistDir "README.txt"
if (Test-Path $readmeSrc) {
    Copy-Item $readmeSrc $readmeDst -Force
}

Write-Host ""
Write-Host "Build OK: $DistDir" -ForegroundColor Green
Write-Host "Zip that folder and send it to others." -ForegroundColor Green
