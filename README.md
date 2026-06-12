# OpsPilot

面向 Linux 服务器的自然语言运维 Agent。OpsPilot 在传统运维工具(系统巡检、日志分析、SSH 批量执行)的基础上,叠加了一层 **AI Agent**:你用自然语言描述问题,由大模型自主决定调用哪些工具、读取结果、推理分析,并给出运维建议。

支持以 **命令行工具** 和 **FastAPI 网络服务** 两种形态运行,并兼容**多家模型厂商** —— OpenAI、Anthropic(Claude),以及通过 OpenAI 兼容接口接入的国内主流模型(DeepSeek、通义千问/DashScope、智谱 GLM、Moonshot Kimi)。

## 功能特性

- **系统巡检** —— 基于 `psutil` 采集 CPU、内存、磁盘指标。
- **日志分析** —— 流式扫描日志,支持按模式/级别/时间过滤与聚合。
- **SSH 批量管理** —— 并发在多台主机上执行命令,单台失败相互隔离。
- **AI Agent 层** —— 通过工具调用循环(tool-calling loop)驱动自然语言请求。
- **多厂商支持** —— 可插拔的 provider 适配器(策略模式 + 注册表),新增厂商只需注册一个类。
- **交互式安装** —— 安装向导引导填写 provider / URL / API Key / 模型名,并在保存前做连通性与工具调用健康检测。
- **凭据安全** —— API Key 以 `SecretStr` 存储,日志中自动脱敏,优先以 `${ENV}` 环境变量引用形式持久化。
- **双入口** —— Typer/Rich 命令行与 FastAPI REST 接口,共用同一套 service 层。

## 项目架构

```
ops_agent/
├── core/        # 系统巡检、日志分析、SSH 管理、领域模型
├── services/    # 供 CLI、web、AI 工具复用的薄服务适配层
├── ai/          # AI Agent 层:providers、工具注册表、agent 循环、安装向导
├── cli/         # Typer 命令行(inspect / analyze / ssh / ai)
└── web/         # FastAPI 应用 + 路由
```

所有运维业务逻辑都集中在 core 层。CLI、web 后端、AI 工具都只是同一套 service 的使用方,不重复实现任何业务逻辑。

## 安装

需要 Python 3.10+。

### 一键交互式安装(推荐)

克隆后运行安装脚本,它会引导你完成环境搭建、选择大模型、录入 API Key,并自动做连通性检测:

```bash
git clone https://github.com/wsy1150524500-sudo/opspilot.git
cd opspilot

# Linux / macOS
bash install.sh

# Windows (PowerShell)
# powershell -ExecutionPolicy Bypass -File install.ps1
```

安装过程会在终端依次询问:接入哪个大模型(ChatGPT / DeepSeek / 通义千问 / 智谱 / Kimi / Claude / 自定义)、模型名称、API Key。API Key 存入 `.env`(权限 600),配置文件 `config/ai.yaml` 中只保留 `${ENV}` 引用,不落明文。

### 手动安装

```bash
git clone https://github.com/wsy1150524500-sudo/opspilot.git
cd opspilot

python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
```

## 使用方法

### 命令行

```bash
# 巡检本机系统(表格输出,或加 --json)
python main.py inspect system
python main.py inspect system --json

# 分析日志文件
python main.py analyze logs /var/log/syslog --pattern "ERROR" --level ERROR

# 从主机清单文件批量执行命令
python main.py ssh run "df -h" --config config/hosts.yaml
```

### AI Agent

先配置模型 provider,向导会在保存前做一次连通性检测:

```bash
python main.py ai setup
```

然后用自然语言提问,Agent 会自主决定调用哪些工具:

```bash
python main.py ai chat "这台服务器为什么变慢了?"
python main.py ai chat "最近 /var/log/syslog 里有报错吗?" --show-transcript
```

### Web 接口

```bash
uvicorn ops_agent.web.server:app --host 0.0.0.0 --port 8000
```

| 方法   | 路径                   | 说明                  |
|--------|------------------------|-----------------------|
| GET    | `/healthz`             | 健康检查              |
| GET    | `/api/v1/system`       | 系统快照              |
| POST   | `/api/v1/logs/analyze` | 日志分析              |
| POST   | `/api/v1/ssh/run`      | SSH 批量执行          |
| POST   | `/api/v1/ai/chat`      | 自然语言 AI Agent     |

交互式 API 文档:`http://<host>:8000/docs`。

## Docker 部署

推荐用 Docker 部署 Web 服务到云服务器。

```bash
# 1. 克隆代码
git clone https://github.com/wsy1150524500-sudo/opspilot.git
cd opspilot

# 2. 准备配置(真实配置与 .env 均已被 git 忽略)
cp config/ai.example.yaml config/ai.yaml
cp config/hosts.example.yaml config/hosts.yaml
cp .env.example .env
# 编辑 config/ai.yaml 填入 provider/模型;编辑 .env 填入对应的 API Key
vim config/ai.yaml
vim .env

# 3. 构建并启动
docker compose up -d --build

# 4. 查看状态与日志
docker compose ps
docker compose logs -f

# 5. 验证(容器仅监听宿主机本地回环)
curl http://127.0.0.1:8000/healthz
```

`docker-compose.yml` 默认把端口绑定到 `127.0.0.1:8000`,**不直接暴露公网**,需通过反向代理(Nginx/Caddy)+ 鉴权对外提供服务。`config/ai.yaml` 以只读卷挂载,改配置无需重建镜像。

也可用同一个镜像跑命令行工具(传入的参数会覆盖默认的 uvicorn 启动命令):

```bash
docker build -t opspilot .
docker run --rm opspilot python main.py inspect system
```

## 配置说明

复制示例配置并填入你自己的值(真实配置文件已被 git 忽略):

```bash
cp config/ai.example.yaml config/ai.yaml
cp config/hosts.example.yaml config/hosts.yaml
```

API Key 应通过环境变量提供,并在 YAML 中以 `${变量名}` 的形式引用。

## 安全须知

> [!WARNING]
> - **切勿在未鉴权的情况下将 Web 接口暴露到公网。** `/api/v1/ssh/run` 和 `/api/v1/ai/chat` 可以在远程主机上执行命令,目前**没有内置鉴权**,且 CORS 默认放开 —— 在任何非本地部署前,务必加上鉴权、收紧 CORS 并限制网络访问。
> - **AI Agent 的 SSH 工具默认关闭**(`ssh_tool_enabled: false`)。仅在配置了严格的 `ssh_command_allowlist` 命令白名单时才启用。
> - **切勿提交真实的 API Key 或凭据。** 请使用 `${ENV}` 引用;`config/ai.yaml` 与 `config/hosts.yaml` 已被 git 忽略。
> - AI Agent 会把系统/日志/命令数据发送给你配置的第三方模型厂商,请留意有哪些数据离开了本机。

## 测试

```bash
pytest
```

测试套件使用 `pytest` 与 `hypothesis`(基于属性的测试),并提供 `FakeProvider` 测试替身,使 AI Agent 循环可在无网络的情况下完成测试。

## 许可证

MIT
