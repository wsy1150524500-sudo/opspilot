"""非交互式连通性检测,供安装脚本调用。

用法:
    python scripts/healthcheck.py [config/ai.yaml]

读取 AI 配置,创建对应 provider,执行一次轻量探测调用。
成功 exit 0,失败 exit 1。API Key 从环境变量读取(配置里用 ${ENV} 引用)。
"""

from __future__ import annotations

import os
import sys

# 确保项目根目录在 import 路径上(脚本可能从任意工作目录被调用)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# 触发 provider 自注册
import ops_agent.ai.providers.openai_provider  # noqa: E402,F401
import ops_agent.ai.providers.anthropic_provider  # noqa: E402,F401
import ops_agent.ai.providers.openai_compatible  # noqa: E402,F401

from ops_agent.ai.config import load_ai_config  # noqa: E402
from ops_agent.ai.errors import AIError  # noqa: E402
from ops_agent.ai.providers.registry import ProviderRegistry  # noqa: E402


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "config/ai.yaml"

    try:
        config = load_ai_config(path)
    except AIError as exc:
        print(f"配置加载失败: {exc}")
        return 1

    try:
        provider = ProviderRegistry.create(config.provider)
    except AIError as exc:
        print(f"Provider 创建失败: {exc}")
        return 1

    result = provider.health_check()

    if result.ok:
        tool = "支持" if result.tool_calling else "未确认"
        print(
            f"连通成功 — 模型 {result.model},延迟 {result.latency_ms}ms,"
            f"工具调用: {tool}"
        )
        return 0

    print(f"连通失败: {result.error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
