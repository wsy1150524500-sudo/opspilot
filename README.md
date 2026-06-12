# OpsPilot

A natural-language-driven operations agent for Linux servers. OpsPilot combines a traditional ops toolkit (system inspection, log analysis, SSH batch execution) with an **AI agent layer** that lets you describe a problem in plain language and have an LLM autonomously decide which tools to run, read the results, reason, and return operational advice.

Works as both a **CLI tool** and a **FastAPI web service**, and supports **multiple model providers** — OpenAI, Anthropic (Claude), and OpenAI-compatible endpoints for Chinese mainstream models (DeepSeek, Qwen/DashScope, Zhipu GLM, Moonshot Kimi).

## Features

- **System inspection** — CPU, memory, and disk metrics via `psutil`.
- **Log analysis** — streaming log scan with pattern/level/time filtering and aggregation.
- **SSH batch management** — run a command across many hosts concurrently with per-host failure isolation.
- **AI agent layer** — natural-language requests driven through an agentic tool-calling loop.
- **Multi-provider support** — pluggable provider adapters (strategy pattern + registry); add a new provider by registering one class.
- **Interactive setup** — a setup wizard prompts for provider/URL/key/model and runs a connectivity + tool-calling health check before saving.
- **Secure credentials** — API keys stored as `SecretStr`, redacted in logs, preferentially persisted as `${ENV}` references.
- **Two surfaces** — a Typer/Rich CLI and a FastAPI REST API, both reusing the same service layer.

## Architecture

```
ops_agent/
├── core/        # System inspector, log analyzer, SSH manager, domain models
├── services/    # Thin service adapters reused by CLI, web, and AI tools
├── ai/          # AI agent layer: providers, tool registry, agent loop, setup wizard
├── cli/         # Typer CLI (inspect / analyze / ssh / ai)
└── web/         # FastAPI app + routers
```

The agent core holds all ops logic. The CLI, web backend, and AI tools are all consumers of the same services — no business logic is duplicated.

## Installation

Requires Python 3.10+.

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

## Usage

### CLI

```bash
# Inspect local system (pretty table, or --json)
python main.py inspect system
python main.py inspect system --json

# Analyze a log file
python main.py analyze logs /var/log/syslog --pattern "ERROR" --level ERROR

# Run a command across hosts from an inventory file
python main.py ssh run "df -h" --config config/hosts.yaml
```

### AI Agent

First, configure a model provider. The wizard runs a connectivity check before saving:

```bash
python main.py ai setup
```

Then ask in natural language — the agent decides which tools to call:

```bash
python main.py ai chat "why is this server slow?"
python main.py ai chat "any errors in /var/log/syslog recently?" --show-transcript
```

### Web API

```bash
uvicorn ops_agent.web.server:app --host 0.0.0.0 --port 8000
```

| Method | Path                   | Description                  |
|--------|------------------------|------------------------------|
| GET    | `/healthz`             | Health check                 |
| GET    | `/api/v1/system`       | System snapshot              |
| POST   | `/api/v1/logs/analyze` | Log analysis                 |
| POST   | `/api/v1/ssh/run`      | SSH batch execution          |
| POST   | `/api/v1/ai/chat`      | Natural-language AI agent    |

Interactive API docs are available at `http://<host>:8000/docs`.

## Configuration

Copy the example configs and fill in your values (real config files are git-ignored):

```bash
cp config/ai.example.yaml config/ai.yaml
cp config/hosts.example.yaml config/hosts.yaml
```

API keys should be supplied via environment variables and referenced as `${VAR_NAME}` in the YAML.

## Security

> [!WARNING]
> - **Never expose the web API publicly without authentication.** The `/api/v1/ssh/run` and `/api/v1/ai/chat` endpoints can execute commands on remote hosts. They currently have **no built-in auth** and CORS is permissive by default — add authentication, tighten CORS, and restrict network access before any non-local deployment.
> - **The SSH tool is disabled for the AI agent by default** (`ssh_tool_enabled: false`). Only enable it with a strict `ssh_command_allowlist`.
> - **Never commit real API keys or credentials.** Use `${ENV}` references; `config/ai.yaml` and `config/hosts.yaml` are git-ignored.
> - The AI agent sends system/log/command data to your configured third-party model provider. Be aware of what data leaves the host.

## Testing

```bash
pytest
```

The suite uses `pytest` and `hypothesis` for property-based tests, with a `FakeProvider` test double so the AI agent loop is tested without network access.

## License

MIT
