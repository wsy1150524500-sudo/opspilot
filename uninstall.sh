#!/usr/bin/env bash
#
# OpsPilot 完全卸载脚本
#
# 用法:
#   cd opspilot
#   bash uninstall.sh
#
# 会引导确认后,删除 OpsPilot 的运行环境、配置、源码和 Docker 资源。
# 最终提示手动删除项目目录(脚本无法删除自身所在目录)。

set -euo pipefail

# ── 颜色输出(与 install.sh 保持一致) ────────────────────
if [ -t 1 ]; then
    BOLD="\033[1m"; GREEN="\033[32m"; RED="\033[31m"
    YELLOW="\033[33m"; CYAN="\033[36m"; DIM="\033[2m"; RESET="\033[0m"
else
    BOLD=""; GREEN=""; RED=""; YELLOW=""; CYAN=""; DIM=""; RESET=""
fi

info()  { echo -e "${CYAN}==>${RESET} $*"; }
ok()    { echo -e "${GREEN}✓${RESET} $*"; }
warn()  { echo -e "${YELLOW}⚠${RESET} $*"; }
err()   { echo -e "${RED}✗${RESET} $*" >&2; }
title() { echo -e "\n${BOLD}$*${RESET}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_DIR_NAME="$(basename "$SCRIPT_DIR")"

# ── 进度条 ────────────────────────────────────────────────
# 用法: progress <当前步骤> <总步骤数> <说明文字>
TOTAL_STEPS=6
progress() {
    local current="$1" total="$2" label="$3"
    local pct=$(( current * 100 / total ))
    local filled=$(( current * 30 / total ))
    local empty=$(( 30 - filled ))
    local bar=""
    for (( i=0; i<filled; i++ )); do bar="${bar}#"; done
    for (( i=0; i<empty;  i++ )); do bar="${bar}-"; done
    printf "\r${CYAN}[%s]${RESET} %3d%% (%d/%d) %s" "$bar" "$pct" "$current" "$total" "$label"
    echo
}

# ── 横幅 ─────────────────────────────────────────────────
echo -e "${BOLD}${RED}"
echo "  ___              ___ _ _      _   "
echo " / _ \\ _ __  ___  | _ (_) |___ | |_ "
echo "| (_) | '_ \\(_-<  |  _/ | / _ \\|  _|"
echo " \\___/| .__/__/   |_| |_|_\\___/ \\__|"
echo "      |_|   OpsPilot 完全卸载"
echo -e "${RESET}"

# ── 列出即将删除的内容 ────────────────────────────────────
title "即将删除的全部内容清单"
echo ""
echo -e "${BOLD}${RED}  【运行环境与数据】${RESET}"
echo -e "    ${RED}●${RESET} .venv/          虚拟环境(含已安装的全部依赖)"
echo -e "    ${RED}●${RESET} .env            API Key 等敏感凭据"
echo -e "    ${RED}●${RESET} config/ai.yaml  AI 配置(含密钥引用)"
echo -e "    ${RED}●${RESET} config/hosts.yaml  主机清单配置"
echo -e "    ${RED}●${RESET} __pycache__/ .pytest_cache/ .hypothesis/ *.pyc  缓存"
echo -e "    ${RED}●${RESET} Docker 容器 opspilot + 镜像 opspilot:latest"
echo ""
echo -e "${BOLD}${RED}  【项目本体】${RESET}"
echo -e "    ${RED}●${RESET} ops_agent/      全部源码(core/services/ai/cli/web)"
echo -e "    ${RED}●${RESET} config/*.example.yaml  配置模板"
echo -e "    ${RED}●${RESET} scripts/        healthcheck 等工具脚本"
echo -e "    ${RED}●${RESET} main.py, requirements.txt, pyproject.toml"
echo -e "    ${RED}●${RESET} Dockerfile, docker-compose.yml, .dockerignore"
echo -e "    ${RED}●${RESET} install.sh, install.ps1, uninstall.sh, uninstall.ps1"
echo -e "    ${RED}●${RESET} README.md, .gitignore, .gitattributes, .env.example"
echo -e "    ${RED}●${RESET} tests/          全部测试文件"
echo ""

# ── 通用 y/n 询问:返回 0 表示 yes,返回 1 表示 no ─────────
# 用法: if ask_yes_no "提示文字"; then ...
ask_yes_no() {
    local prompt="$1" reply
    while true; do
        read -r -p "$prompt" reply
        case "$reply" in
            [yY]) return 0 ;;
            [nN]|"") return 1 ;;
            *) warn "请输入 y 或 N" ;;
        esac
    done
}

# ── 第一道确认 ────────────────────────────────────────────
if ! ask_yes_no "$(echo -e "${BOLD}${RED}确认要完全卸载并删除 OpsPilot 吗?此操作不可逆 [y/N]: ${RESET}")"; then
    info "已取消卸载,什么都没变。"
    exit 0
fi

# ── 第二道确认:是否删 .git ────────────────────────────────
DELETE_GIT=false
if ask_yes_no "$(echo -e "${BOLD}是否同时删除 .git 版本库?删除后将丢失本地提交历史 [y/N]: ${RESET}")"; then
    DELETE_GIT=true
fi

echo ""
info "开始卸载..."
echo ""

STEP=0

# ── 步骤 1: 停止并移除 Docker 容器 ───────────────────────
STEP=$((STEP + 1))
progress "$STEP" "$TOTAL_STEPS" "停止并移除 Docker 容器..."
if command -v docker >/dev/null 2>&1 && [ -f "docker-compose.yml" ]; then
    docker compose down 2>/dev/null || true
    ok "Docker 容器已移除"
else
    echo -e "  ${DIM}(跳过:Docker 未安装或无 docker-compose.yml)${RESET}"
fi
sleep 0.3

# ── 步骤 2: 删除 Docker 镜像 ─────────────────────────────
STEP=$((STEP + 1))
progress "$STEP" "$TOTAL_STEPS" "删除 Docker 镜像..."
if command -v docker >/dev/null 2>&1; then
    docker rmi opspilot:latest 2>/dev/null || true
    ok "Docker 镜像已删除(若存在)"
else
    echo -e "  ${DIM}(跳过:Docker 未安装)${RESET}"
fi
sleep 0.3

# ── 步骤 3: 删除虚拟环境 ─────────────────────────────────
STEP=$((STEP + 1))
progress "$STEP" "$TOTAL_STEPS" "删除虚拟环境 .venv/..."
if [ -d ".venv" ]; then
    rm -rf ".venv"
    ok ".venv/ 已删除"
else
    echo -e "  ${DIM}(跳过:.venv/ 不存在)${RESET}"
fi
sleep 0.3

# ── 步骤 4: 删除 .env 和真实配置 ─────────────────────────
STEP=$((STEP + 1))
progress "$STEP" "$TOTAL_STEPS" "删除凭据与真实配置..."
for f in ".env" "config/ai.yaml" "config/hosts.yaml"; do
    if [ -e "$f" ]; then
        rm -f "$f"
        ok "$f 已删除"
    fi
done
sleep 0.3

# ── 步骤 5: 清理缓存 ─────────────────────────────────────
STEP=$((STEP + 1))
progress "$STEP" "$TOTAL_STEPS" "清理 __pycache__ / .pytest_cache / .hypothesis / *.pyc..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".hypothesis" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
ok "缓存已清理"
sleep 0.3

# ── 步骤 6: 删除项目文件与源码 ───────────────────────────
STEP=$((STEP + 1))
progress "$STEP" "$TOTAL_STEPS" "删除项目源码与文件..."

# 删除顶层目录
for d in ops_agent config scripts tests .kiro; do
    if [ -d "$d" ]; then
        rm -rf "$d"
        ok "$d/ 已删除"
    fi
done

# 删除顶层文件
for f in \
    main.py requirements.txt pyproject.toml \
    Dockerfile docker-compose.yml .dockerignore \
    install.sh install.ps1 uninstall.sh uninstall.ps1 \
    README.md .gitignore .gitattributes .env.example
do
    if [ -e "$f" ]; then
        rm -f "$f"
        ok "$f 已删除"
    fi
done

# 删除 .claude 目录(如果存在)
if [ -d ".claude" ]; then
    rm -rf ".claude"
    ok ".claude/ 已删除"
fi

# 可选:删除 .git
if [ "$DELETE_GIT" = true ] && [ -d ".git" ]; then
    rm -rf ".git"
    ok ".git/ 已删除"
fi

sleep 0.3

# ── 完成 ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}  ✓ OpsPilot 已卸载${RESET}"
echo ""

warn "项目目录本身及本卸载脚本仍残留,请手动完成最终清除:"
echo ""
echo -e "  ${BOLD}cd .. && rm -rf \"${PROJECT_DIR_NAME}\"${RESET}"
echo ""

if [ "$DELETE_GIT" = false ]; then
    warn "你选择保留了 .git 版本库,它也会随上述命令一起删除。"
    echo ""
fi

warn "若你曾为 OpsPilot 配置过 systemd 服务、cron 定时任务或反向代理(Nginx/Caddy),请手动移除。"
echo ""
