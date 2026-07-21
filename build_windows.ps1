# OpenManus Windows 一键打包脚本
# 用法：在项目根目录执行  .\build_windows.ps1
# 产物：dist\OpenManus\  （将该文件夹打成 zip 即可分发）

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root "my_ai_env\Scripts\python.exe"
$VenvPip = Join-Path $Root "my_ai_env\Scripts\pip.exe"
$DistDir = Join-Path $Root "dist\OpenManus"

Write-Host "==> 检查虚拟环境..." -ForegroundColor Cyan
if (-not (Test-Path $VenvPython)) {
    Write-Error "未找到虚拟环境: $VenvPython"
}

Write-Host "==> 安装/更新 PyInstaller..." -ForegroundColor Cyan
& $VenvPip install -U pyinstaller

Write-Host "==> 开始打包（可能需要数分钟）..." -ForegroundColor Cyan
& $VenvPython -m PyInstaller --noconfirm --clean (Join-Path $Root "OpenManus.spec")
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller 打包失败，退出码: $LASTEXITCODE"
}

if (-not (Test-Path $DistDir)) {
    Write-Error "未找到产物目录: $DistDir"
}

Write-Host "==> 复制运行时资源到 exe 旁..." -ForegroundColor Cyan

# config：可执行文件旁必须有 config.toml
$configSrc = Join-Path $Root "config"
$configDst = Join-Path $DistDir "config"
if (Test-Path $configDst) {
    Remove-Item $configDst -Recurse -Force
}
Copy-Item $configSrc $configDst -Recurse -Force

# knowledge（可选知识库）
$knowledgeSrc = Join-Path $Root "knowledge"
if (Test-Path $knowledgeSrc) {
    $knowledgeDst = Join-Path $DistDir "knowledge"
    if (Test-Path $knowledgeDst) {
        Remove-Item $knowledgeDst -Recurse -Force
    }
    Copy-Item $knowledgeSrc $knowledgeDst -Recurse -Force
}

# 工作目录与日志目录
New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "workspace") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "logs") | Out-Null

# 分发说明（简短 txt，避免再单独维护 md）
$readme = @"
OpenManus 使用说明
==================
1. 解压后双击 OpenManus.exe 启动
2. 在界面中填写 API Key，输入任务后点「开始执行」
3. 如需修改模型等配置，编辑同目录下 config\config.toml
4. 浏览器相关功能依赖本机已安装 Chrome/Edge；若失败请自行安装浏览器
5. 请勿把含真实 API Key 的 config.toml 发给他人
"@
Set-Content -Path (Join-Path $DistDir "使用说明.txt") -Value $readme -Encoding UTF8

Write-Host ""
Write-Host "打包完成: $DistDir" -ForegroundColor Green
Write-Host "请将该文件夹压缩成 zip 后发给对方。" -ForegroundColor Green
