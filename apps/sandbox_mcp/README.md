# DinButler MCP Server

Model Context Protocol (MCP) server for DinButler sandbox integration with Claude Code.

## Overview

This MCP server exposes 19 tools for managing DinButler sandboxes through Claude Code. It wraps the `sbx` CLI commands via subprocess calls, providing a seamless integration between AI assistants and Docker-based sandbox environments.

## Architecture

- **Framework**: FastMCP (Model Context Protocol)
- **Backend**: Subprocess calls to `sbx` CLI
- **LOC**: ~568 lines (563 server.py + 5 __init__.py)
- **Tools**: 19 total (7 lifecycle + 10 file ops + 2 execution)

## Tools

### Sandbox Lifecycle (7 tools)

1. **init_sandbox** - Initialize sandbox and save ID locally
2. **create_sandbox** - Create sandbox without state tracking
3. **connect_sandbox** - Connect to existing sandbox
4. **kill_sandbox** - Stop and remove sandbox
5. **get_sandbox_info** - Get detailed sandbox metadata
6. **check_sandbox_status** - Check if sandbox is running
7. **list_sandboxes** - List all sandboxes

### File Operations (10 tools)

8. **list_files** - List directory contents
9. **read_file** - Read file contents
10. **write_file** - Write content to file
11. **file_exists** - Check if path exists
12. **get_file_info** - Get file metadata
13. **remove_file** - Delete file or directory
14. **create_directory** - Create directory
15. **rename_file** - Rename or move file
16. **upload_file** - Upload from host to sandbox
17. **download_file** - Download from sandbox to host

### Command Execution (2 tools)

18. **execute_command** - Run command in sandbox with full options
19. **sandbox_fork** - Placeholder for future AI workflow orchestration

## Usage

### Running the Server

```bash
# Standalone mode
python -m apps.sandbox_mcp.server

# Or via MCP protocol
mcp run apps.sandbox_mcp
```

### Configuration for Claude Code

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dinbutler": {
      "command": "python",
      "args": ["-m", "apps.sandbox_mcp.server"],
      "cwd": "/Users/amund/dinbutler"
    }
  }
}
```

### Example Tool Calls

```python
# Initialize a sandbox
init_sandbox(template="python", timeout=600, envs='{"DEBUG": "1"}')

# Execute commands
execute_command(
    command="python script.py",
    cwd="/workspace",
    env_vars='{"API_KEY": "xxx"}',
    timeout=120
)

# File operations
write_file(path="/app/config.json", content='{"key": "value"}')
result = read_file(path="/app/config.json")

# List and manage
list_sandboxes()
get_sandbox_info()
```

## Environment Variables

The server automatically handles environment conflicts:

- **VIRTUAL_ENV**: Removed to avoid uv package manager conflicts
- **Current directory**: Preserved from caller's context

## Error Handling

All tools return JSON responses:

```json
// Success
{
  "sandbox_id": "sb_abc123",
  "status": "running"
}

// Error
{
  "error": "Sandbox not found",
  "exit_code": 1
}
```

## Dependencies

- **mcp.server.fastmcp**: FastMCP framework
- **subprocess**: CLI command execution
- **json**: Response parsing
- **os**: Environment management

## CLI Mapping

| MCP Tool | CLI Command |
|----------|-------------|
| init_sandbox | `sbx init --json --template X --timeout Y` |
| create_sandbox | `sbx sandbox create --json --template X` |
| connect_sandbox | `sbx sandbox connect [ID]` |
| kill_sandbox | `sbx sandbox kill [ID]` |
| get_sandbox_info | `sbx sandbox info --json [ID]` |
| check_sandbox_status | `sbx sandbox status [ID]` |
| list_sandboxes | `sbx sandbox list --json` |
| list_files | `sbx files ls --json --depth X [ID] PATH` |
| read_file | `sbx files read [ID] PATH` |
| write_file | `sbx files write [ID] PATH CONTENT` |
| file_exists | `sbx files exists [ID] PATH` |
| get_file_info | `sbx files info --json [ID] PATH` |
| remove_file | `sbx files remove [ID] PATH` |
| create_directory | `sbx files mkdir [ID] PATH` |
| rename_file | `sbx files rename [ID] OLD NEW` |
| upload_file | `sbx files upload [ID] LOCAL REMOTE` |
| download_file | `sbx files download [ID] REMOTE LOCAL` |
| execute_command | `sbx exec run --json [OPTIONS] [ID] COMMAND` |

## State Management

The server leverages DinButler's local state tracking:

- `.dinbutler/sandbox_id` stores the last active sandbox ID
- Commands with optional `sandbox_id` parameter use this state
- Enables seamless multi-command workflows without ID repetition

## Future Enhancements

- **sandbox_fork**: Parallel AI agent workflows (coming soon)
- **Streaming output**: Real-time command output via MCP streams
- **PTY support**: Interactive terminal sessions
- **File watching**: Real-time filesystem change events

## Development

```bash
# Test syntax
python -m py_compile apps/sandbox_mcp/server.py

# Run locally
cd /Users/amund/dinbutler
python -m apps.sandbox_mcp.server

# Integration test
python -c "from apps.sandbox_mcp import mcp; print(mcp)"
```

## License

Part of the DinButler project.
