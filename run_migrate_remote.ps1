# 小白一键 UTC 迁移工具 - PowerShell 版（双击运行）
# 用法：右键此文件 → Run with PowerShell

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TikTok 数据 UTC 迁移工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检测 python
$pyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyCmd = "py"
} else {
    Write-Host "未找到 Python，请先安装 Python 并加入 PATH。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}
Write-Host "使用 Python: $pyCmd ($(&$pyCmd --version))" -ForegroundColor Green
Write-Host ""

try {
    & $pyCmd "backend\scripts\run_migrate_remote.py"
} catch {
    Write-Host ""
    Write-Host "运行出错: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "脚本已结束。如果上方有错误，请截图发给助手。" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Read-Host "按回车关闭"
