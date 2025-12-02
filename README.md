# DinButler

**Your Butler for AI Sandboxes** - Local E2B-compatible sandbox execution using Docker.

> *"Din" means "Your" in Norwegian, pronounced "Dean"*

```bash
pip install dinbutler && python -c "from dinbutler import Sandbox; print(Sandbox.create().commands.run('echo Hello from DinButler').stdout)"
```

```python
from dinbutler import Sandbox

with Sandbox.create() as sandbox:
    result = sandbox.commands.run("echo Hello from DinButler!")
    print(result.stdout)  # Hello from DinButler!
```

DinButler provides isolated sandbox environments for AI agents to safely execute code, manipulate files, and run commands - all locally on your machine with zero cloud costs.

## Why DinButler?

- **Zero Cost** - No cloud API fees, usage limits, or subscriptions
- **Privacy First** - All code execution stays on your machine
- **E2B Compatible** - Drop-in replacement for E2B SDK
- **Fast** - No network latency, instant sandbox creation
- **Offline Ready** - Works without internet connection

## Claude Code Integration

DinButler includes full Claude Code integration via MCP (Model Context Protocol), similar to [agent-sandboxes](https://github.com/disler/agent-sandboxes) but running locally.

### Quick Setup

```bash
# Install with MCP support
pip install "dinbutler[all]"

# Copy MCP config to Claude Code
cp .mcp.json.sample ~/.claude/mcp.json
# Edit the cwd path in mcp.json to point to your dinbutler installation
```

### Features

| Feature | Description |
|---------|-------------|
| **MCP Server** | 19 tools for sandbox control from Claude |
| **CLI (`sbx`)** | Full sandbox management from terminal |
| **Parallel Forks (`obox`)** | Run multiple Claude agents experimenting in parallel |
| **Slash Commands** | `/prime`, `/prime_sandbox`, `/prime_obox` |

### Example: Claude in "YOLO Mode"

Once configured, Claude can safely execute any code in isolated containers:

```
You: Create a sandbox and run some Python code

Claude: [Uses init_sandbox tool]
        [Uses write_file to create script.py]
        [Uses execute_command: python script.py]
        [Uses kill_sandbox when done]
```

The container auto-destroys after timeout - your system stays safe.

### Parallel Agent Experiments

```bash
# Run 5 Claude agents trying different approaches
obox https://github.com/user/repo \
  --forks 5 \
  --prompt "Refactor the auth module"
```

📖 **Full Documentation**: See [docs/plans/claude-code-integration.md](docs/plans/claude-code-integration.md)

## Use Cases

### MCP (Model Context Protocol) Servers

Build MCP servers that give AI assistants safe code execution:

```python
from dinbutler import Sandbox

# MCP tool handler for code execution
def execute_code(code: str, language: str = "python") -> str:
    with Sandbox.create(timeout=30) as sandbox:
        sandbox.files.write("/tmp/script.py", code)
        result = sandbox.commands.run(f"python /tmp/script.py")
        return result.stdout if result.exit_code == 0 else result.stderr
```

### Agent-to-Agent (A2A) Locally

Enable local AI agents to collaborate through shared sandboxes:

```python
from dinbutler import Sandbox

# Shared workspace for multiple agents
sandbox = Sandbox.create(timeout=300)

# Agent 1: Write code
sandbox.files.write("/workspace/app.py", agent1_code)

# Agent 2: Review and test
result = sandbox.commands.run("python /workspace/app.py")

# Agent 3: Analyze output
sandbox.files.write("/workspace/results.json", result.stdout)
```

### AI Developer Tool Integration

DinButler works seamlessly with modern AI coding assistants:

| Tool | Integration |
|------|-------------|
| **Claude Code** (Anthropic) | Safe code execution environment |
| **Gemini CLI** (Google) | Isolated testing sandbox |
| **Codex** (OpenAI) | Secure code runner |
| **GitHub Copilot** | Test generated code safely |
| **Warp** | AI-powered terminal sandbox |
| **Cursor** | Code execution backend |
| **Aider** | Safe code testing |

### CI/CD and Testing

Run untrusted code in isolated containers:

```python
from dinbutler import Sandbox

def test_user_submission(code: str) -> dict:
    with Sandbox.create(timeout=10) as sandbox:
        sandbox.files.write("/test/solution.py", code)
        result = sandbox.commands.run("python -m pytest /test/")
        return {
            "passed": result.exit_code == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
```

## Installation

```bash
pip install dinbutler
```

### Prerequisites

**macOS** (with Colima):
```bash
brew install colima docker
colima start --vm-type=vz
```

**Linux** (with Docker):
```bash
# Docker should work directly
sudo apt install docker.io
```

**Windows** (with Docker Desktop or WSL2):
```bash
# Use Docker Desktop or WSL2 with Docker
```

### Build the default template:

```bash
dinbutler build-templates
```

## Quick Start

### Basic Usage

```python
from dinbutler import Sandbox

# Create a sandbox (auto-cleanup after 60 seconds)
sandbox = Sandbox.create(timeout=60)

# Run commands
result = sandbox.commands.run("echo 'Hello from DinButler!'")
print(result.stdout)  # Hello from DinButler!

# File operations
sandbox.files.write("/tmp/data.txt", "Hello World")
content = sandbox.files.read("/tmp/data.txt")
print(content)  # Hello World

# List files
entries = sandbox.files.list("/tmp")
for entry in entries:
    print(f"{entry.name} ({entry.type})")

# Clean up
sandbox.kill()
```

### Context Manager (Recommended)

```python
from dinbutler import Sandbox

with Sandbox.create(timeout=60) as sandbox:
    result = sandbox.commands.run("python --version")
    print(result.stdout)
# Sandbox automatically killed on exit
```

### Async Support

```python
from dinbutler import AsyncSandbox
import asyncio

async def main():
    async with AsyncSandbox.create(timeout=60) as sandbox:
        result = await sandbox.commands.run("ls -la")
        print(result.stdout)

asyncio.run(main())
```

### Background Processes

```python
from dinbutler import Sandbox

with Sandbox.create(timeout=120) as sandbox:
    # Start a background process
    handle = sandbox.commands.start("python -m http.server 8000")

    # Do other work...
    sandbox.commands.run("curl http://localhost:8000")

    # Stop the background process
    handle.kill()
```

### Environment Variables

```python
sandbox = Sandbox.create(
    timeout=60,
    envs={
        "API_KEY": "secret",
        "DEBUG": "true"
    }
)
```

### Custom Templates

```python
# Use built-in templates
sandbox = Sandbox.create(template="python")  # Python environment
sandbox = Sandbox.create(template="node")    # Node.js environment

# Or use any Docker image
sandbox = Sandbox.create(template="ubuntu:22.04")
```

## CLI Commands

```bash
# Start the API server
dinbutler server
dinbutler server --host 0.0.0.0 --port 9000

# Build Docker templates
dinbutler build-templates
dinbutler build-templates --template python

# List running sandboxes
dinbutler list

# Clean up all sandboxes
dinbutler cleanup
```

## API Reference

### Sandbox

```python
class Sandbox:
    # Creation
    @classmethod
    def create(cls, template="default", timeout=300, envs=None, metadata=None) -> Sandbox

    @classmethod
    def connect(cls, sandbox_id: str) -> Sandbox

    # Properties
    sandbox_id: str

    # Methods
    def is_running(self) -> bool
    def set_timeout(self, timeout: int) -> None
    def kill(self) -> bool
```

### Commands Module

```python
sandbox.commands.run(cmd, timeout=60, env=None, cwd=None, user=None) -> CommandResult
sandbox.commands.start(cmd, env=None, cwd=None, user=None) -> CommandHandle
sandbox.commands.list() -> List[ProcessInfo]
```

### Files Module

```python
sandbox.files.read(path, format="text") -> str | bytes
sandbox.files.write(path, data) -> WriteInfo
sandbox.files.list(path, depth=1) -> List[EntryInfo]
sandbox.files.exists(path) -> bool
sandbox.files.remove(path) -> None
sandbox.files.watch(path, on_change=None) -> WatchHandle
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                          │
│              (AI Agent, MCP Server, CLI Tool)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      DinButler SDK                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Sandbox   │  │   Files     │  │     Commands        │  │
│  │   Manager   │──│   Service   │──│     Service         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Docker / Colima                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Sandbox 1   │  │  Sandbox 2   │  │  Sandbox N   │       │
│  │  (Container) │  │  (Container) │  │  (Container) │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DINBUTLER_SOCKET` | Docker socket path | Auto-detected |
| `DOCKER_HOST` | Docker host URL | Auto-detected |

### Socket Auto-Detection

DinButler automatically finds the Docker socket in these locations:
1. `~/.colima/default/docker.sock` (Colima)
2. `~/.colima/docker.sock` (Colima alternate)
3. `/var/run/docker.sock` (Docker Desktop / Linux)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black dinbutler tests
ruff check dinbutler tests

# Type checking
mypy dinbutler
```

## Comparison with E2B

| Feature | DinButler | E2B |
|---------|-----------|-----|
| **Cost** | Free | Pay-per-use |
| **Privacy** | Local only | Cloud |
| **Latency** | ~100ms | ~500ms+ |
| **Offline** | Yes | No |
| **API** | E2B-compatible | Native |
| **Scaling** | Single machine | Cloud scale |

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines first.

---

**DinButler** - *Your Butler for AI Sandboxes*
