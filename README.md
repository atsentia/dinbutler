# DinButler 🤖

**Local AI sandbox execution - E2B-compatible, zero cost, privacy-first**

DinButler provides isolated sandbox environments for AI agents to safely execute code, manipulate files, and run commands - all locally on your machine. It's a local complement for the E2B SDK that works with Docker/Colima, giving you zero cloud costs, complete privacy, and offline capability.

Perfect for MCP servers, agent-to-agent workflows, and integration with AI developer tools like Claude Code, Gemini CLI, GitHub Copilot, Warp and others.

## ✨ Features

- **E2B-Compatible API**: Drop-in replacement for `e2b-code-interpreter` - same interface, local execution
- **Docker/Colima Backend**: Works with any Docker-compatible runtime
- **Zero Cloud Costs**: No API keys, no usage fees, no internet required
- **Complete Privacy**: Your code never leaves your machine
- **Multi-Language Support**: Python, JavaScript, Bash, and more
- **File Operations**: Read, write, list, and manage files in isolated containers
- **Command Execution**: Run shell commands with full control over environment
- **Async Support**: Both synchronous and async APIs available

## 📦 Installation

```bash
pip install dinbutler
```

### Prerequisites

- Python 3.10+
- Docker or Colima installed and running

## 🚀 Quick Start

### Basic Usage

```python
from dinbutler import Sandbox

# Create a sandbox and run code
with Sandbox.create() as sandbox:
    result = sandbox.run_code("print('Hello, World!')")
    print(result.text)  # Output: Hello, World!
```

### Running Different Languages

```python
from dinbutler import Sandbox

with Sandbox.create() as sandbox:
    # Python (default)
    result = sandbox.run_code("print(2 + 2)")
    print(result.text)  # Output: 4

    # Bash
    result = sandbox.run_code("echo 'Hello from Bash'", language="bash")
    print(result.text)  # Output: Hello from Bash

    # Shell commands
    result = sandbox.run_code("ls -la /", language="sh")
    print(result.text)
```

### File Operations

```python
from dinbutler import Sandbox

with Sandbox.create() as sandbox:
    # Write a file
    sandbox.files.write("/tmp/hello.txt", "Hello, File!")

    # Read a file
    content = sandbox.files.read("/tmp/hello.txt")
    print(content)  # Output: Hello, File!

    # List files
    files = sandbox.files.list("/tmp")
    for f in files:
        print(f"{f.name} - {'dir' if f.is_dir else 'file'}")

    # Check if file exists
    exists = sandbox.files.exists("/tmp/hello.txt")
    print(exists)  # Output: True

    # Create directories
    sandbox.files.mkdir("/tmp/my/nested/dir")

    # Remove files
    sandbox.files.remove("/tmp/hello.txt")
```

### Running Commands

```python
from dinbutler import Sandbox

with Sandbox.create() as sandbox:
    # Run a command
    result = sandbox.commands.run("ls -la /home")
    print(result.stdout)
    print(f"Exit code: {result.exit_code}")

    # Run with environment variables
    result = sandbox.commands.run(
        "echo $MY_VAR",
        envs={"MY_VAR": "Hello from env!"}
    )
    print(result.stdout)  # Output: Hello from env!

    # Run in a specific directory
    result = sandbox.commands.run("pwd", cwd="/tmp")
    print(result.stdout)  # Output: /tmp
```

### Async Usage

```python
import asyncio
from dinbutler import AsyncSandbox

async def main():
    async with await AsyncSandbox.create() as sandbox:
        result = await sandbox.run_code("print('Hello, async!')")
        print(result.text)

asyncio.run(main())
```

### Custom Docker Image

```python
from dinbutler import Sandbox

# Use a custom Docker image
with Sandbox.create(template="node:20-slim") as sandbox:
    result = sandbox.run_code(
        "console.log('Hello from Node.js!')",
        language="javascript"
    )
    print(result.text)
```

### Environment Variables

```python
from dinbutler import Sandbox

with Sandbox.create(envs={"API_KEY": "secret"}) as sandbox:
    result = sandbox.run_code("""
import os
print(f"API_KEY is set: {'API_KEY' in os.environ}")
    """)
    print(result.text)
```

### Handling Errors

```python
from dinbutler import Sandbox

with Sandbox.create() as sandbox:
    result = sandbox.run_code("raise ValueError('Something went wrong!')")

    if result.error:
        print(f"Error: {result.error.name}")
        print(f"Message: {result.error.value}")
        print(f"Traceback:\n{result.error.traceback}")
    else:
        print(result.text)
```

### Output Streaming

```python
from dinbutler import Sandbox

def handle_stdout(output: str) -> None:
    print(f"STDOUT: {output}")

def handle_stderr(output: str) -> None:
    print(f"STDERR: {output}")

with Sandbox.create() as sandbox:
    result = sandbox.run_code(
        "print('Hello!'); import sys; print('Error!', file=sys.stderr)",
        on_stdout=handle_stdout,
        on_stderr=handle_stderr,
    )
```

## 🔧 API Reference

### Sandbox

#### `Sandbox.create(template=None, timeout=300, envs=None, cwd="/home/user")`

Create a new sandbox instance.

- `template`: Docker image to use (default: `python:3.12-slim`)
- `timeout`: Container timeout in seconds
- `envs`: Environment variables to set
- `cwd`: Working directory in the container

#### `sandbox.run_code(code, language="python", on_stdout=None, on_stderr=None, envs=None, timeout=None, cwd=None)`

Execute code in the sandbox.

- `code`: The code to execute
- `language`: Programming language (`python`, `javascript`, `bash`, `sh`)
- `on_stdout`: Callback for stdout output
- `on_stderr`: Callback for stderr output
- `envs`: Additional environment variables
- `timeout`: Execution timeout in seconds
- `cwd`: Working directory for execution

Returns an `Execution` object.

#### `sandbox.files`

File operations interface:
- `write(path, content)`: Write content to a file
- `read(path)`: Read file content
- `list(path)`: List directory contents
- `exists(path)`: Check if path exists
- `mkdir(path, parents=True)`: Create directory
- `remove(path)`: Remove file or directory

#### `sandbox.commands`

Command execution interface:
- `run(command, cwd=None, envs=None, timeout=None, on_stdout=None, on_stderr=None)`: Run a shell command

### Execution

Result of code execution.

- `text`: Combined text output
- `html`: HTML output (if any)
- `markdown`: Markdown output (if any)
- `results`: List of Result objects
- `logs`: List of log lines
- `error`: ExecutionError if execution failed
- `exit_code`: Process exit code

### AsyncSandbox

Async version of Sandbox with the same API, using `async`/`await`.

## 🤝 E2B Compatibility

DinButler is designed to be a drop-in replacement for the E2B Code Interpreter SDK. The main differences:

| Feature | E2B | DinButler |
|---------|-----|-----------|
| Execution | Cloud | Local (Docker) |
| Cost | Usage-based | Free |
| Privacy | Data sent to cloud | Fully local |
| Internet | Required | Optional |
| API Key | Required | Not needed |

### Migration from E2B

```python
# Before (E2B)
from e2b_code_interpreter import Sandbox

# After (DinButler)
from dinbutler import Sandbox

# The rest of your code stays the same!
```

## 🛠️ Development

### Setup

```bash
# Clone the repository
git clone https://github.com/atsentia/dinbutler.git
cd dinbutler

# Install with development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dinbutler
```

### Linting

```bash
# Run ruff linter
ruff check src/

# Run type checking
mypy src/
```

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [E2B](https://e2b.dev) for the excellent SDK design that this project is compatible with
- The Docker team for containerization technology
