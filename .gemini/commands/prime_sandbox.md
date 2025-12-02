# DinButler MCP Server - Gemini CLI Tool Reference

This guide covers all available tools when using DinButler's MCP server with the Gemini CLI.

## Overview

DinButler exposes secure Docker sandboxes through the Model Context Protocol (MCP). All operations run in isolated containers with automatic cleanup.

## Sandbox Management

### `init`

Initialize the DinButler sandbox system.

```bash
gemini sandbox init
```

**Use when:** First time setup, or after Docker cleanup.

---

### `create`

Create a new isolated sandbox from a template.

```bash
gemini sandbox create --template="python" --timeout=300
```

**Arguments:**
- `--template`: "default", "python", "node", "gemini", or custom template name
- `--timeout`: Maximum execution time in seconds (default: 300)

**Returns:** Sandbox ID (e.g., "sandbox_abc123")

---

### `list`

List all running sandboxes with their status.

```bash
gemini sandbox list
```

**Returns:** A list of sandboxes with their ID, template, uptime, and status.

---

### `kill`

Terminate and remove a sandbox.

```bash
gemini sandbox kill --id="sandbox_abc123"
```

**Arguments:**
- `--id`: The ID of the sandbox to terminate.

**Note:** Always kill sandboxes when done to free resources.

## File Management

### `files write`

Write content to a file in the sandbox.

```bash
gemini sandbox files write --id="sandbox_abc123" --path="/app/script.py" --content="print('Hello World')"
```

**Arguments:**
- `--id`: Target sandbox ID.
- `--path`: Absolute path in the container (usually under `/app`).
- `--content`: File content as a string.

---

### `files read`

Read file contents from the sandbox.

```bash
gemini sandbox files read --id="sandbox_abc123" --path="/app/output.txt"
```

**Arguments:**
- `--id`: Target sandbox ID.
- `--path`: Absolute path to read.

**Returns:** File content as a string.

---

### `files list`

List files and directories in the sandbox.

```bash
gemini sandbox files list --id="sandbox_abc123" --path="/app" --recursive
```

**Arguments:**
- `--id`: Target sandbox ID.
- `--path`: Directory to list.
- `--recursive`: List subdirectories.

---

### `files remove`

Delete a file or directory from the sandbox.

```bash
gemini sandbox files remove --id="sandbox_abc123" --path="/app/temp.txt"
```

**Arguments:**
- `--id`: Target sandbox ID.
- `--path`: Path to remove.

## Command Execution

### `exec`

Run a command in the sandbox and get output.

```bash
gemini sandbox exec --id="sandbox_abc123" --command="python /app/script.py" --timeout=60
```

**Arguments:**
- `--id`: Target sandbox ID.
- `--command`: Shell command to execute.
- `--timeout`: Command timeout in seconds (default: 30).
