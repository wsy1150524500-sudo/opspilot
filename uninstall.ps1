<#
.SYNOPSIS
    OpsPilot 完全卸载脚本 (Windows / PowerShell 版)

.DESCRIPTION
    对应 uninstall.sh 的 Windows 版本。会引导确认后,删除 OpsPilot 的
    运行环境、配置、源码和 Docker 资源。最终提示手动删除项目目录。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File uninstall.ps1
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$ProjectDirName = Split-Path -Leaf $ScriptDir

# ── 输出函数 ──────────────────────────────────────────────
function Write-Info  { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok    { param($m) Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn  { param($m) Write-Host "  [!] $m" -ForegroundColor Yellow }
function Write-Err   { param($m) Write-Host "  [X] $m" -ForegroundColor Red }
function Write-Title { param($m) Write-Host "`n$m" -ForegroundColor White }

# ── 进度条 ────────────────────────────────────────────────
function Show-Progress {
    param([int]$Current, [int]$Total, [string]$Label)
    $pct    = [int]($Current * 100 / $Total)
    $filled = [int]($Current * 30 / $Total)
    $empty  = 30 - $filled
    $bar    = ("#" * $filled) + ("-" * $empty)
    Write-Host "`r" -NoNewline
    Write-Host "[$bar] " -ForegroundColor Cyan -NoNewline
    Write-Host ("{0,3}% ({1}/{2}) {3}" -f $pct, $Current, $Total, $Label) -NoNewline
    Write-Host "                    "
}

# ── 横幅 ──────────────────────────────────────────────────
Write-Host ""
Write-Host "  ___              ___ _ _      _   " -ForegroundColor Red
Write-Host " / _ \ _ __  ___  | _ (_) |___ | |_ " -ForegroundColor Red
Write-Host "| (_) | '_ \(_-<  |  _/ | / _ \|  _|" -ForegroundColor Red
Write-Host " \___/| .__/__/   |_| |_|\___/ \__|" -ForegroundColor Red
Write-Host "      |_|   OpsPilot 完全卸载"       -ForegroundColor Red
Write-Host ""

# ── 列出即将删除的内容 ────────────────────────────────────
Write-Title "即将删除的全部内容清单"
Write-Host ""
Write-Host "  【运行环境与数据】" -ForegroundColor Red
Write-Host "    ● .venv/          虚拟环境(含已安装的全部依赖)"
Write-Host "    ● .env            API Key 等敏感凭据"
Write-Host "    ● config/ai.yaml  AI 配置(含密钥引用)"
Write-Host "    ● config/hosts.yaml  主机清单配置"
Write-Host "    ● __pycache__/ .pytest_cache/ .hypothesis/ *.pyc  缓存"
Write-Host "    ● Docker 容器 opspilot + 镜像 opspilot:latest"
Write-Host ""
Write-Host "  【项目本体】" -ForegroundColor Red
Write-Host "    ● ops_agent/      全部源码(core/services/ai/cli/web)"
Write-Host "    ● config/*.example.yaml  配置模板"
Write-Host "    ● scripts/        healthcheck 等工具脚本"
Write-Host "    ● main.py, requirements.txt, pyproject.toml"
Write-Host "    ● Dockerfile, docker-compose.yml, .dockerignore"
Write-Host "    ● install.sh, install.ps1, uninstall.sh, uninstall.ps1"
Write-Host "    ● README.md, .gitignore, .gitattributes, .env.example"
Write-Host "    ● tests/          全部测试文件"
Write-Host ""

# ── 通用 y/n 询问:返回 $true 表示 yes,$false 表示 no ─────
function Ask-YesNo {
    param([string]$Prompt)
    while ($true) {
        $reply = (Read-Host $Prompt).ToLower()
        if ($reply -eq "y") { return $true }
        if ($reply -eq "n" -or $reply -eq "") { return $false }
        Write-Warn "请输入 y 或 N"
    }
}

# ── 第一道确认 ────────────────────────────────────────────
if (-not (Ask-YesNo "确认要完全卸载并删除 OpsPilot 吗?此操作不可逆 [y/N]")) {
    Write-Info "已取消卸载,什么都没变。"
    exit 0
}

# ── 第二道确认:是否删 .git ────────────────────────────────
$DeleteGit = Ask-YesNo "是否同时删除 .git 版本库?删除后将丢失本地提交历史 [y/N]"

Write-Host ""
Write-Info "开始卸载..."
Write-Host ""

$TotalSteps = 6
$Step = 0

# ── 步骤 1: 停止并移除 Docker 容器 ───────────────────────
$Step++
Show-Progress $Step $TotalSteps "停止并移除 Docker 容器..."
$hasDocker = [bool](Get-Command docker -ErrorAction SilentlyContinue)
if ($hasDocker -and (Test-Path "docker-compose.yml")) {
    try { docker compose down 2>$null } catch { }
    Write-Ok "Docker 容器已移除"
} else {
    Write-Host "  (跳过:Docker 未安装或无 docker-compose.yml)" -ForegroundColor DarkGray
}
Start-Sleep -Milliseconds 300

# ── 步骤 2: 删除 Docker 镜像 ─────────────────────────────
$Step++
Show-Progress $Step $TotalSteps "删除 Docker 镜像..."
if ($hasDocker) {
    try { docker rmi opspilot:latest 2>$null } catch { }
    Write-Ok "Docker 镜像已删除(若存在)"
} else {
    Write-Host "  (跳过:Docker 未安装)" -ForegroundColor DarkGray
}
Start-Sleep -Milliseconds 300

# ── 步骤 3: 删除虚拟环境 ─────────────────────────────────
$Step++
Show-Progress $Step $TotalSteps "删除虚拟环境 .venv/..."
if (Test-Path ".venv") {
    Remove-Item -Recurse -Force ".venv"
    Write-Ok ".venv/ 已删除"
} else {
    Write-Host "  (跳过:.venv/ 不存在)" -ForegroundColor DarkGray
}
Start-Sleep -Milliseconds 300

# ── 步骤 4: 删除 .env 和真实配置 ─────────────────────────
$Step++
Show-Progress $Step $TotalSteps "删除凭据与真实配置..."
foreach ($f in @(".env", "config/ai.yaml", "config/hosts.yaml")) {
    if (Test-Path $f) {
        Remove-Item -Force $f
        Write-Ok "$f 已删除"
    }
}
Start-Sleep -Milliseconds 300

# ── 步骤 5: 清理缓存 ─────────────────────────────────────
$Step++
Show-Progress $Step $TotalSteps "清理 __pycache__ / .pytest_cache / .hypothesis / *.pyc..."
foreach ($pattern in @("__pycache__", ".pytest_cache", ".hypothesis")) {
    Get-ChildItem -Recurse -Directory -Filter $pattern -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
Get-ChildItem -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue
Write-Ok "缓存已清理"
Start-Sleep -Milliseconds 300

# ── 步骤 6: 删除项目文件与源码 ───────────────────────────
$Step++
Show-Progress $Step $TotalSteps "删除项目源码与文件..."

# 删除顶层目录
foreach ($d in @("ops_agent", "config", "scripts", "tests", ".kiro", ".claude")) {
    if (Test-Path $d) {
        Remove-Item -Recurse -Force $d
        Write-Ok "$d/ 已删除"
    }
}

# 删除顶层文件
foreach ($f in @(
    "main.py", "requirements.txt", "pyproject.toml",
    "Dockerfile", "docker-compose.yml", ".dockerignore",
    "install.sh", "install.ps1", "uninstall.sh", "uninstall.ps1",
    "README.md", ".gitignore", ".gitattributes", ".env.example"
)) {
    if (Test-Path $f) {
        Remove-Item -Force $f
        Write-Ok "$f 已删除"
    }
}

# 可选:删除 .git
if ($DeleteGit -and (Test-Path ".git")) {
    Remove-Item -Recurse -Force ".git"
    Write-Ok ".git/ 已删除"
}

Start-Sleep -Milliseconds 300

# ── 完成 ──────────────────────────────────────────────────
Write-Host ""
Write-Host "  ✓ OpsPilot 已卸载" -ForegroundColor Green
Write-Host ""

Write-Warn "项目目录本身及本卸载脚本仍残留,请手动完成最终清除:"
Write-Host ""
Write-Host "  cd .. ; Remove-Item -Recurse -Force `"$ProjectDirName`"" -ForegroundColor White
Write-Host ""

if (-not $DeleteGit) {
    Write-Warn "你选择保留了 .git 版本库,它也会随上述命令一起删除。"
    Write-Host ""
}

Write-Warn "若你曾为 OpsPilot 配置过计划任务或反向代理,请手动移除。"
Write-Host ""
