# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

# 不生成 .pyc、输出不缓冲,便于容器日志实时查看
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先只拷依赖清单,利用构建缓存(依赖不变就不重装)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷源码
COPY ops_agent/ ./ops_agent/
COPY main.py ./
COPY config/ ./config/

# 以非 root 用户运行,降低风险
RUN useradd --create-home --uid 10001 opspilot \
    && chown -R opspilot:opspilot /app
USER opspilot

EXPOSE 8000

# 默认启动 Web 服务。只监听容器内 0.0.0.0,对外暴露由 compose/反代控制
CMD ["uvicorn", "ops_agent.web.server:app", "--host", "0.0.0.0", "--port", "8000"]
