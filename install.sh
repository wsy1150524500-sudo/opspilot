#!/usr/bin/env bash
#
# OpsPilot 交互式安装脚本
#
# 用法:
#   git clone https://github.com/wsy1150524500-sudo/opspilot.git
#   cd opspilot
#   bash install.sh
#
# 脚本会:
#   1. 检查 Python 环境
#   2. 创建虚拟环境并安装依赖
#   3. 交互式询问接入的大模型、URL、API Key
#   4. 写入配置文件(API Key 存入 .env,配置里用 ${ENV} 引用)
#   5. 执行连通性检测
#   6. 提示后续启动方式(本地 / Docker)

set -euo pipefail

# ── 颜色输出 ─────────────────────────────────────────────
if [ -t 1 ]; then
    BOLD="\033[1m"; GREEN="\033[32m"; RED="\033[31m"
    YELLOW="\033[33m"; CYAN="\033[36m"; RESET="\033[0m"
else
    BOLD=""; GREEN=""; RED=""; YELLOW=""; CYAN=""; RESET=""
fi

info()  { echo -e "${CYAN}==>${RESET} $*"; }
ok()    { echo -e "${GREEN}✓${RESET} $*"; }
warn()  { echo -e "${YELLOW}⚠${RESET} $*"; }
err()   { echo -e "${RED}✗${RESET} $*" >&2; }
title() { echo -e "\n${BOLD}$*${RESET}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv"
AI_CONFIG="config/ai.yaml"
HOSTS_CONFIG="config/hosts.yaml"
ENV_FILE=".env"

# ── 横幅 ─────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
echo "  ___              ___ _ _      _   "
echo " / _ \\ _ __  ___  | _ (_) |___ | |_ "
echo "| (_) | '_ \\(_-<  |  _/ | / _ \\|  _|"
echo " \\___/| .__/__/   |_| |_|_\\___/ \\__|"
echo "      |_|   OpsPilot 安装向导"
echo -e "${RESET}"

# ─────────────────────────────────────────────────────────
# 1. 检查 Python
# ─────────────────────────────────────────────────────────
title "[1/6] 检查 Python 环境"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    err "未找到 $PYTHON_BIN,请先安装 Python 3.11+"
    exit 1
fi
PY_VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
ok "检测到 Python $PY_VER"

# ─────────────────────────────────────────────────────────
# 2. 虚拟环境 + 依赖
# ─────────────────────────────────────────────────────────
title "[2/6] 创建虚拟环境并安装依赖"
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    ok "已创建虚拟环境 $VENV_DIR"
else
    ok "复用已有虚拟环境 $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
info "安装依赖中(可能需要几分钟)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "依赖安装完成"

# ─────────────────────────────────────────────────────────
# 3. 交互式选择大模型
# ─────────────────────────────────────────────────────────
title "[3/6] 配置大模型接入"
echo "请选择要接入的大模型:"
echo "  a. ChatGPT (OpenAI)"
echo "  b. DeepSeek (深度求索)"
echo "  c. 通义千问 (阿里 DashScope)"
echo "  d. 智谱 GLM"
echo "  e. Kimi (Moonshot)"
echo "  f. Claude (Anthropic)"
echo "  g. 其他 OpenAI 兼容接口(手动填 URL)"
echo

PROVIDER_KIND=""     # openai | anthropic | openai_compatible
BASE_URL=""
DEFAULT_MODEL=""
ENV_NAME=""
PROVIDER_LABEL=""

while true; do
    read -r -p "请输入选项编号 [a-g]: " choice
    case "$choice" in
        a|A)
            PROVIDER_KIND="openai";            PROVIDER_LABEL="ChatGPT (OpenAI)"
            BASE_URL="";                       DEFAULT_MODEL="gpt-4o"
            ENV_NAME="OPENAI_API_KEY";         break ;;
        b|B)
            PROVIDER_KIND="openai_compatible"; PROVIDER_LABEL="DeepSeek"
            BASE_URL="https://api.deepseek.com/v1"; DEFAULT_MODEL="deepseek-chat"
            ENV_NAME="DEEPSEEK_API_KEY";       break ;;
        c|C)
            PROVIDER_KIND="openai_compatible"; PROVIDER_LABEL="通义千问"
            BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"; DEFAULT_MODEL="qwen-plus"
            ENV_NAME="DASHSCOPE_API_KEY";      break ;;
        d|D)
            PROVIDER_KIND="openai_compatible"; PROVIDER_LABEL="智谱 GLM"
            BASE_URL="https://open.bigmodel.cn/api/paas/v4"; DEFAULT_MODEL="glm-4-plus"
            ENV_NAME="ZHIPU_API_KEY";          break ;;
        e|E)
            PROVIDER_KIND="openai_compatible"; PROVIDER_LABEL="Kimi (Moonshot)"
            BASE_URL="https://api.moonshot.cn/v1"; DEFAULT_MODEL="moonshot-v1-8k"
            ENV_NAME="MOONSHOT_API_KEY";       break ;;
        f|F)
            PROVIDER_KIND="anthropic";         PROVIDER_LABEL="Claude (Anthropic)"
            BASE_URL="";                       DEFAULT_MODEL="claude-sonnet-4-20250514"
            ENV_NAME="ANTHROPIC_API_KEY";      break ;;
        g|G)
            PROVIDER_KIND="openai_compatible"; PROVIDER_LABEL="自定义 OpenAI 兼容接口"
            read -r -p "请输入接口 Base URL: " BASE_URL
            if [ -z "$BASE_URL" ]; then err "Base URL 不能为空"; continue; fi
            DEFAULT_MODEL=""
            ENV_NAME="COMPAT_API_KEY";         break ;;
        *)
            warn "无效选项 '$choice',请输入 a 到 g 之间的字母" ;;
    esac
done

ok "已选择: $PROVIDER_LABEL"

# 模型名
read -r -p "请输入模型名称 [默认 ${DEFAULT_MODEL:-无}]: " MODEL_NAME
MODEL_NAME="${MODEL_NAME:-$DEFAULT_MODEL}"
if [ -z "$MODEL_NAME" ]; then
    err "模型名称不能为空"
    exit 1
fi

# API Key(隐藏输入)
echo
read -r -s -p "请输入 ${PROVIDER_LABEL} 的 API Key: " API_KEY
echo
if [ -z "$API_KEY" ]; then
    err "API Key 不能为空"
    exit 1
fi
ok "API Key 已录入(将存入 $ENV_FILE,不会明文写入配置文件)"

# ─────────────────────────────────────────────────────────
# 4. 写入配置文件
# ─────────────────────────────────────────────────────────
title "[4/6] 写入配置文件"

mkdir -p config

# 4a. API Key 写入 .env(更新或追加)
touch "$ENV_FILE"
if grep -q "^${ENV_NAME}=" "$ENV_FILE" 2>/dev/null; then
    # 替换已有行(用 | 作分隔符避免 key 中的 / 冲突)
    tmp="$(mktemp)"
    grep -v "^${ENV_NAME}=" "$ENV_FILE" > "$tmp" || true
    mv "$tmp" "$ENV_FILE"
fi
echo "${ENV_NAME}=${API_KEY}" >> "$ENV_FILE"
chmod 600 "$ENV_FILE"
ok "API Key 已写入 $ENV_FILE (权限 600)"

# 4b. 生成 config/ai.yaml(api_key 用 ${ENV} 引用)
{
    echo "provider:"
    echo "  kind: ${PROVIDER_KIND}"
    if [ -n "$BASE_URL" ]; then
        echo "  base_url: ${BASE_URL}"
    fi
    echo "  api_key: \${${ENV_NAME}}"
    echo "  model: ${MODEL_NAME}"
    echo "  timeout_s: 30"
    echo "  max_tokens: 1024"
    echo "  temperature: 0.2"
    echo "max_iterations: 8"
    echo "ssh_tool_enabled: false"
    echo "ssh_command_allowlist: []"
    echo "system_prompt: >"
    echo "  You are an operations assistant. Use the provided tools to inspect"
    echo "  the system and logs before answering. Be concise."
} > "$AI_CONFIG"
ok "已生成 $AI_CONFIG"

# 4c. 主机清单(默认生成空清单,避免示例主机导致校验失败;按需手动添加主机)
if [ ! -f "$HOSTS_CONFIG" ]; then
    {
        echo "ssh_timeout_s: 15"
        echo "max_concurrency: 10"
        echo "hosts: []"
    } > "$HOSTS_CONFIG"
    ok "已生成空的 $HOSTS_CONFIG (如需 SSH 批量管理,参考 config/hosts.example.yaml 添加主机)"
fi

# ─────────────────────────────────────────────────────────
# 5. 连通性检测
# ─────────────────────────────────────────────────────────
title "[5/6] 连通性检测"
info "正在向 $PROVIDER_LABEL 发起探测调用..."

# 让 healthcheck.py 能读到刚录入的 key
set +u
export "${ENV_NAME}=${API_KEY}"
set -u

if python scripts/healthcheck.py "$AI_CONFIG"; then
    ok "连通性检测通过"
else
    warn "连通性检测未通过。配置已保存,但请检查 API Key / URL / 网络后重试:"
    echo "    source $VENV_DIR/bin/activate && python scripts/healthcheck.py $AI_CONFIG"
fi

# ─────────────────────────────────────────────────────────
# 6. 完成提示
# ─────────────────────────────────────────────────────────
title "[6/6] 安装完成 🎉"
echo
echo "后续使用方式:"
echo
echo -e "  ${BOLD}命令行 AI 问答:${RESET}"
echo "    source $VENV_DIR/bin/activate"
echo "    set -a && source $ENV_FILE && set +a       # 加载 API Key"
echo "    python main.py ai chat \"这台服务器为什么变慢了?\""
echo
echo -e "  ${BOLD}启动 Web 服务(本地):${RESET}"
echo "    set -a && source $ENV_FILE && set +a"
echo "    uvicorn ops_agent.web.server:app --host 127.0.0.1 --port 8000"
echo
echo -e "  ${BOLD}Docker 部署:${RESET}"
echo "    docker compose up -d --build"
echo
warn "安全提醒: Web 接口默认无鉴权,切勿裸暴露公网。请置于反向代理 + 鉴权之后。"
echo
