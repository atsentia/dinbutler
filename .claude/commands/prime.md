# DinButler Quick Reference

DinButler provides local Docker-based sandboxes for AI code execution with full isolation and security.

## Quick Start

```python
from dinbutler import Sandbox

# Create sandbox with template
sandbox = Sandbox.create(template="python", timeout=300)

# Run commands
result = sandbox.commands.run("python --version")
print(result.stdout)  # Python 3.11.x

# File operations
sandbox.files.write("/app/script.py", "print('Hello from sandbox!')")
content = sandbox.files.read("/app/script.py")
files = sandbox.files.list("/app")

# Cleanup when done
sandbox.kill()
```

## Available Templates

- **default** - Ubuntu 22.04 with bash, curl, git, vim
- **python** - Python 3.11 + pip, numpy, pandas, requests
- **node** - Node.js 20 + npm, TypeScript, common packages
- **custom** - Build your own with Dockerfile

## Core Features

### Command Execution
```python
# Simple command
result = sandbox.commands.run("ls -la /app")

# Interactive shell
result = sandbox.commands.run("python", input="print(2+2)\n")

# With environment variables
result = sandbox.commands.run("env", env={"DEBUG": "1"})
```

### File Management
```python
# Write files
sandbox.files.write("/app/config.json", '{"key": "value"}')

# Read files
data = sandbox.files.read("/app/config.json")

# List directory
files = sandbox.files.list("/app", recursive=True)

# Remove files
sandbox.files.remove("/app/temp.txt")
```

### Sandbox Lifecycle
```python
# List all running sandboxes
sandboxes = Sandbox.list()

# Get sandbox by ID
sandbox = Sandbox.get("sandbox_abc123")

# Check status
status = sandbox.status()

# Kill sandbox
sandbox.kill()
```

## MCP Server Integration

When using DinButler's MCP server with Claude Desktop or Claude Code, these tools are automatically available:

- Sandbox: `init_sandbox`, `create_sandbox`, `kill_sandbox`, `list_sandboxes`
- Files: `read_file`, `write_file`, `list_files`, `remove_file`
- Commands: `execute_command`

For full MCP documentation, use `/prime_sandbox`.

## Safety Features

- Full Docker isolation (network, filesystem, process)
- Automatic timeout enforcement (default 300s)
- Resource limits (CPU, memory, disk)
- Automatic cleanup on errors
- No host filesystem access

## Common Patterns

```python
# Test Python code safely
sandbox = Sandbox.create("python")
sandbox.files.write("/app/test.py", user_code)
result = sandbox.commands.run("python /app/test.py")
sandbox.kill()

# Run untrusted script
sandbox = Sandbox.create("default")
result = sandbox.commands.run("bash /app/script.sh", timeout=60)
print(result.exit_code, result.stdout, result.stderr)
sandbox.kill()

# Multi-step workflow
sandbox = Sandbox.create("node")
sandbox.files.write("/app/package.json", pkg_json)
sandbox.commands.run("npm install")
result = sandbox.commands.run("npm test")
sandbox.kill()
```

## Debugging

```python
# Check sandbox logs
result = sandbox.commands.run("cat /tmp/app.log")

# Inspect environment
result = sandbox.commands.run("env")

# Check running processes
result = sandbox.commands.run("ps aux")
```

For parallel execution workflows, see `/prime_obox`.
