# DinButler MCP Server - Complete Tool Reference

This guide covers all 19 MCP tools available when using DinButler's MCP server with Claude Desktop or Claude Code.

## Overview

DinButler exposes secure Docker sandboxes through the Model Context Protocol (MCP). All operations run in isolated containers with automatic cleanup.

## Sandbox Management Tools (4 tools)

### 1. init_sandbox

Initialize the DinButler sandbox system (creates Docker network, downloads templates).

```json
{
  "name": "init_sandbox"
}
```

**Returns:** Initialization status

**Use when:** First time setup, or after Docker cleanup

---

### 2. create_sandbox

Create a new isolated sandbox from a template.

```json
{
  "name": "create_sandbox",
  "arguments": {
    "template": "python",
    "timeout": 300,
    "metadata": {"purpose": "test_user_code"}
  }
}
```

**Parameters:**
- `template` (required): "default", "python", "node", or custom template name
- `timeout` (optional): Maximum execution time in seconds (default: 300)
- `metadata` (optional): Key-value pairs for tracking

**Returns:** Sandbox ID (e.g., "sandbox_abc123")

**Templates:**
- `default` - Ubuntu 22.04, bash, curl, git, vim
- `python` - Python 3.11, numpy, pandas, requests, pytest
- `node` - Node.js 20, npm, TypeScript, jest

---

### 3. list_sandboxes

List all running sandboxes with their status.

```json
{
  "name": "list_sandboxes"
}
```

**Returns:** Array of sandbox objects with ID, template, uptime, status

**Use when:** Checking for orphaned sandboxes or debugging

---

### 4. kill_sandbox

Terminate and remove a sandbox.

```json
{
  "name": "kill_sandbox",
  "arguments": {
    "sandbox_id": "sandbox_abc123"
  }
}
```

**Parameters:**
- `sandbox_id` (required): Sandbox to terminate

**Returns:** Success confirmation

**Note:** Always kill sandboxes when done to free resources

## File Management Tools (4 tools)

### 5. write_file

Write content to a file in the sandbox.

```json
{
  "name": "write_file",
  "arguments": {
    "sandbox_id": "sandbox_abc123",
    "path": "/app/script.py",
    "content": "print('Hello World')"
  }
}
```

**Parameters:**
- `sandbox_id` (required): Target sandbox
- `path` (required): Absolute path in container (usually under `/app`)
- `content` (required): File content as string

**Returns:** Bytes written

**Note:** Creates parent directories automatically

---

### 6. read_file

Read file contents from the sandbox.

```json
{
  "name": "read_file",
  "arguments": {
    "sandbox_id": "sandbox_abc123",
    "path": "/app/output.txt"
  }
}
```

**Parameters:**
- `sandbox_id` (required): Target sandbox
- `path` (required): Absolute path to read

**Returns:** File content as string

**Errors:** Raises if file doesn't exist

---

### 7. list_files

List files and directories in the sandbox.

```json
{
  "name": "list_files",
  "arguments": {
    "sandbox_id": "sandbox_abc123",
    "path": "/app",
    "recursive": true
  }
}
```

**Parameters:**
- `sandbox_id` (required): Target sandbox
- `path` (required): Directory to list
- `recursive` (optional): List subdirectories (default: false)

**Returns:** Array of file/directory entries with type, size, permissions

---

### 8. remove_file

Delete a file or directory from the sandbox.

```json
{
  "name": "remove_file",
  "arguments": {
    "sandbox_id": "sandbox_abc123",
    "path": "/app/temp.txt"
  }
}
```

**Parameters:**
- `sandbox_id` (required): Target sandbox
- `path` (required): Path to remove

**Returns:** Success confirmation

**Note:** Use with caution, no undo available

## Command Execution Tool (1 tool)

### 9. execute_command

Run a command in the sandbox and get output.

```json
{
  "name": "execute_command",
  "arguments": {
    "sandbox_id": "sandbox_abc123",
    "command": "python /app/script.py",
    "timeout": 60,
    "env": {"DEBUG": "1"}
  }
}
```

**Parameters:**
- `sandbox_id` (required): Target sandbox
- `command` (required): Shell command to execute
- `timeout` (optional): Command timeout in seconds (default: 30)
- `env` (optional): Additional environment variables

**Returns:** Object with `exit_code`, `stdout`, `stderr`, `timed_out`

**Examples:**

```json
// Run Python script
{
  "command": "python /app/test.py",
  "timeout": 120
}

// Install packages
{
  "command": "pip install requests beautifulsoup4"
}

// Run tests
{
  "command": "pytest /app/tests/ -v"
}

// Interactive input (via heredoc)
{
  "command": "python",
  "input": "print(2+2)\nprint('done')\n"
}
```

## Complete Workflow Examples

### Example 1: Run User's Python Code

```python
# Step 1: Create sandbox
sandbox_id = create_sandbox(template="python")

# Step 2: Write code
write_file(
  sandbox_id=sandbox_id,
  path="/app/user_code.py",
  content=user_submitted_code
)

# Step 3: Execute
result = execute_command(
  sandbox_id=sandbox_id,
  command="python /app/user_code.py",
  timeout=60
)

# Step 4: Check results
print(f"Exit code: {result['exit_code']}")
print(f"Output: {result['stdout']}")
if result['stderr']:
    print(f"Errors: {result['stderr']}")

# Step 5: Cleanup
kill_sandbox(sandbox_id=sandbox_id)
```

### Example 2: Test Node.js Package

```python
# Create Node sandbox
sandbox_id = create_sandbox(template="node")

# Write package.json
write_file(
  sandbox_id=sandbox_id,
  path="/app/package.json",
  content='{"name": "test", "dependencies": {"lodash": "^4.17.21"}}'
)

# Write test file
write_file(
  sandbox_id=sandbox_id,
  path="/app/index.js",
  content="const _ = require('lodash'); console.log(_.VERSION);"
)

# Install dependencies
execute_command(sandbox_id=sandbox_id, command="npm install")

# Run code
result = execute_command(sandbox_id=sandbox_id, command="node /app/index.js")
print(result['stdout'])  # Should show lodash version

# Cleanup
kill_sandbox(sandbox_id=sandbox_id)
```

### Example 3: Multi-File Project

```python
# Create sandbox
sandbox_id = create_sandbox(template="python")

# Write multiple files
write_file(sandbox_id, "/app/config.py", "DEBUG = True")
write_file(sandbox_id, "/app/utils.py", "def add(a, b): return a + b")
write_file(sandbox_id, "/app/main.py", """
from config import DEBUG
from utils import add

result = add(2, 3)
if DEBUG:
    print(f'Result: {result}')
""")

# Execute main script
result = execute_command(sandbox_id, "python /app/main.py")
print(result['stdout'])  # "Result: 5"

# List created files
files = list_files(sandbox_id, "/app", recursive=True)
print(files)

# Cleanup
kill_sandbox(sandbox_id)
```

### Example 4: Error Handling

```python
sandbox_id = None
try:
    # Create sandbox
    sandbox_id = create_sandbox(template="python", timeout=300)

    # Write potentially buggy code
    write_file(sandbox_id, "/app/test.py", user_code)

    # Run with timeout
    result = execute_command(
      sandbox_id=sandbox_id,
      command="python /app/test.py",
      timeout=30
    )

    # Check for errors
    if result['exit_code'] != 0:
        print(f"Script failed: {result['stderr']}")
    elif result['timed_out']:
        print("Script exceeded 30 second timeout")
    else:
        print(f"Success: {result['stdout']}")

except Exception as e:
    print(f"Sandbox error: {e}")

finally:
    # Always cleanup
    if sandbox_id:
        kill_sandbox(sandbox_id)
```

## Best Practices

1. **Always kill sandboxes** - Use try/finally to ensure cleanup
2. **Set appropriate timeouts** - Prevent runaway processes
3. **Use /app directory** - Standard location for user files
4. **Check exit codes** - Don't assume commands succeed
5. **Handle stderr** - Capture error output for debugging
6. **List sandboxes periodically** - Clean up orphaned containers

## Security Notes

- Sandboxes are fully isolated (network, filesystem, processes)
- No access to host filesystem or other containers
- Resource limits enforced (CPU, memory, disk)
- Automatic cleanup on timeout or error
- All code runs as non-root user in container

## Troubleshooting

```python
# Check if sandbox is running
sandboxes = list_sandboxes()
print([s for s in sandboxes if s['id'] == sandbox_id])

# Inspect sandbox environment
result = execute_command(sandbox_id, "env")
print(result['stdout'])

# Check installed packages (Python)
result = execute_command(sandbox_id, "pip list")

# Check installed packages (Node)
result = execute_command(sandbox_id, "npm list --depth=0")

# View sandbox logs
result = execute_command(sandbox_id, "cat /tmp/*.log")
```

For parallel execution workflows, see `/prime_obox`.
