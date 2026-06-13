<#
.SYNOPSIS
    OpsPilot 交互式安装脚本 (Windows / PowerShell 版)

.DESCRIPTION
    对应 install.sh 的 Windows 版本。会创建虚拟环境、安装依赖、
    交互式询问大模型与 API Key、写入配置、执行连通性检测。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonBin   = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$VenvDir     = ".venv"
$AiConfig    = "config/ai.yaml"
$HostsConfig = "config/hosts.yaml"
$EnvFile     = ".env"

function Write-Info  { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok    { param($m) Write-Host "[OK] $m" -ForegroundColor Green }
function Write-Warn  { param($m) Write-Host "[!] $m" -ForegroundColor Yellow }
function Write-Err   { param($m) Write-Host "[X] $m" -ForegroundColor Red }
function Write-Title { param($m) Write-Host "`n$m" -ForegroundColor White }

Write-Host ""
Write-Host "  OpsPilot 安装向导" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Python
Write-Title "[1/6] 检查 Python 环境"
try {
    $pyVer = & $PythonBin -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Ok "检测到 Python $pyVer"
} catch {
    Write-Err "未找到 $PythonBin,请先安装 Python 3.11+"
    exit 1
}

# 2. 虚拟环境 + 依赖
Write-Title "[2/6] 创建虚拟环境并安装依赖"
if (-not (Test-Path $VenvDir)) {
    & $PythonBin -m venv $VenvDir
    Write-Ok "已创建虚拟环境 $VenvDir"
} else {
    Write-Ok "复用已有虚拟环境 $VenvDir"
}
$VenvPy = Join-Path $VenvDir "Scripts/python.exe"
Write-Info "安装依赖中(可能需要几分钟)..."
& $VenvPy -m pip install --quiet --upgrade pip
& $VenvPy -m pip install --quiet -r requirements.txt
Write-Ok "依赖安装完成"

# 3. 交互式选择大模型
Write-Title "[3/6] 配置大模型接入"
Write-Host "请选择要接入的大模型:"
Write-Host "  a. ChatGPT (OpenAI)"
Write-Host "  b. DeepSeek (深度求索)"
Write-Host "  c. 通义千问 (阿里 DashScope)"
Write-Host "  d. 智谱 GLM"
Write-Host "  e. Kimi (Moonshot)"
Write-Host "  f. Claude (Anthropic)"
Write-Host "  g. 其他 OpenAI 兼容接口(手动填 URL)"
Write-Host ""

$ProviderKind = ""; $BaseUrl = ""; $DefaultModel = ""; $EnvName = ""; $ProviderLabel = ""

while ($true) {
    $choice = Read-Host "请输入选项编号 [a-g]"
    switch ($choice.ToLower()) {
        "a" { $ProviderKind="openai";            $ProviderLabel="ChatGPT (OpenAI)"; $BaseUrl="";  $DefaultModel="gpt-4o";                     $EnvName="OPENAI_API_KEY";    break }
        "b" { $ProviderKind="openai_compatible"; $ProviderLabel="DeepSeek";         $BaseUrl="https://api.deepseek.com/v1";                  $DefaultModel="deepseek-chat";   $EnvName="DEEPSEEK_API_KEY";  break }
        "c" { $ProviderKind="openai_compatible"; $ProviderLabel="通义千问";          $BaseUrl="https://dashscope.aliyuncs.com/compatible-mode/v1"; $DefaultModel="qwen-plus";  $EnvName="DASHSCOPE_API_KEY"; break }
        "d" { $ProviderKind="openai_compatible"; $ProviderLabel="智谱 GLM";          $BaseUrl="https://open.bigmodel.cn/api/paas/v4";        $DefaultModel="glm-4-plus";      $EnvName="ZHIPU_API_KEY";     break }
        "e" { $ProviderKind="openai_compatible"; $ProviderLabel="Kimi (Moonshot)";  $BaseUrl="https://api.moonshot.cn/v1";                  $DefaultModel="moonshot-v1-8k";  $EnvName="MOONSHOT_API_KEY";  break }
        "f" { $ProviderKind="anthropic";         $ProviderLabel="Claude (Anthropic)"; $BaseUrl=""; $DefaultModel="claude-sonnet-4-20250514"; $EnvName="ANTHROPIC_API_KEY"; break }
        "g" {
            $ProviderKind="openai_compatible"; $ProviderLabel="自定义 OpenAI 兼容接口"; $EnvName="COMPAT_API_KEY"
            $BaseUrl = Read-Host "请输入接口 Base URL"
            if ([string]::IsNullOrWhiteSpace($BaseUrl)) { Write-Err "Base URL 不能为空"; continue }
            $DefaultModel=""; break
        }
        default { Write-Warn "无效选项 '$choice',请输入 a 到 g 之间的字母" }
    }
    if ($ProviderKind -ne "") { break }
}
Write-Ok "已选择: $ProviderLabel"

# 模型名
$prompt = if ($DefaultModel) { "请输入模型名称 [默认 $DefaultModel]" } else { "请输入模型名称" }
$ModelName = Read-Host $prompt
if ([string]::IsNullOrWhiteSpace($ModelName)) { $ModelName = $DefaultModel }
if ([string]::IsNullOrWhiteSpace($ModelName)) { Write-Err "模型名称不能为空"; exit 1 }

# API Key(隐藏输入)
$secureKey = Read-Host "请输入 $ProviderLabel 的 API Key" -AsSecureString
$ApiKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey))
if ([string]::IsNullOrWhiteSpace($ApiKey)) { Write-Err "API Key 不能为空"; exit 1 }
Write-Ok "API Key 已录入(将存入 $EnvFile)"

# 4. 写入配置
Write-Title "[4/6] 写入配置文件"
if (-not (Test-Path "config")) { New-Item -ItemType Directory -Path "config" | Out-Null }

# 4a. .env
$envLines = @()
if (Test-Path $EnvFile) {
    $envLines = Get-Content $EnvFile | Where-Object { $_ -notmatch "^$EnvName=" }
}
$envLines += "$EnvName=$ApiKey"
$envLines | Set-Content -Path $EnvFile -Encoding UTF8
Write-Ok "API Key 已写入 $EnvFile"

# 4b. config/ai.yaml
$yaml = @("provider:", "  kind: $ProviderKind")
if ($BaseUrl) { $yaml += "  base_url: $BaseUrl" }
$yaml += @(
    "  api_key: `${$EnvName}",
    "  model: $ModelName",
    "  timeout_s: 30",
    "  max_tokens: 1024",
    "  temperature: 0.2",
    "max_iterations: 8",
    "ssh_tool_enabled: false",
    "ssh_command_allowlist: []",
    "system_prompt: >",
    "  You are an operations assistant. Use the provided tools to inspect",
    "  the system and logs before answering. Be concise."
)
$yaml | Set-Content -Path $AiConfig -Encoding UTF8
Write-Ok "已生成 $AiConfig"

# 4c. hosts
if ((-not (Test-Path $HostsConfig)) -and (Test-Path "config/hosts.example.yaml")) {
    Copy-Item "config/hosts.example.yaml" $HostsConfig
    Write-Ok "已从示例生成 $HostsConfig"
}

# 5. 连通性检测
Write-Title "[5/6] 连通性检测"
Write-Info "正在向 $ProviderLabel 发起探测调用..."
[System.Environment]::SetEnvironmentVariable($EnvName, $ApiKey)
& $VenvPy scripts/healthcheck.py $AiConfig
if ($LASTEXITCODE -eq 0) {
    Write-Ok "连通性检测通过"
} else {
    Write-Warn "连通性检测未通过。配置已保存,请检查 API Key / URL / 网络后重试。"
}

# 6. 完成
Write-Title "[6/6] 安装完成"
Write-Host ""
Write-Host "命令行 AI 问答:"
Write-Host "    .venv\Scripts\python.exe main.py ai chat `"这台服务器为什么变慢了?`""
Write-Host ""
Write-Host "启动 Web 服务:"
Write-Host "    .venv\Scripts\uvicorn.exe ops_agent.web.server:app --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Warn "安全提醒: Web 接口默认无鉴权,切勿裸暴露公网。"
Write-Host ""
