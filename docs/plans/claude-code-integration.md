# DinButler Claude Code Integration Plan

## Overview

Add full-featured Claude Code integration to DinButler, matching the capabilities of [disler/agent-sandboxes](https://github.com/disler/agent-sandboxes) but using local Docker/Colima instead of E2B cloud.

**Target Repository**: `/Users/amund/dinbutler`
**Reference**: `https://github.com/disler/agent-sandboxes`
**Architecture**: CLI subprocess wrapper (MCP wraps CLI commands)
**Estimated LOC**: ~3,000 lines

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Claude Code / Claude Desktop                  │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 apps/sandbox_mcp/server.py                   │
│              FastMCP Server (19+ tools)                      │
│   ┌──────────┬──────────┬──────────┬───────────────┐        │
│   │ Sandbox  │  File    │   Exec   │   Workflow    │        │
│   │ (6)      │  (10)    │   (2)    │   (1)         │        │
│   └──────────┴──────────┴──────────┴───────────────┘        │
└────────────────────────┬────────────────────────────────────┘
                         │ subprocess
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 apps/sandbox_cli/main.py                     │
│              Click CLI (sbx command)                         │
│   ┌──────────┬──────────┬──────────┬───────────────┐        │
│   │ sbx init │ sbx      │ sbx      │ sbx exec      │        │
│   │ cleanup  │ sandbox  │ files    │               │        │
│   └──────────┴──────────┴──────────┴───────────────┘        │
└────────────────────────┬────────────────────────────────────┘
                         │ Python SDK
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 dinbutler/ (existing)                        │
│           Sandbox, Files, Commands Services                  │
└────────────────────────┬────────────────────────────────────┘
                         │ Docker SDK
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Docker / Colima                              │
│              Local Container Runtime                         │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
dinbutler/                          # Repository root
├── dinbutler/                      # Core SDK (existing)
├── apps/                           # NEW: Applications
│   ├── sandbox_cli/                # Click CLI
│   │   ├── __init__.py
│   │   ├── main.py                 # Entry point (~120 LOC)
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── sandbox.py          # Lifecycle commands (~180 LOC)
│   │   │   ├── files.py            # File operations (~200 LOC)
│   │   │   └── exec.py             # Command execution (~150 LOC)
│   │   └── modules/
│   │       ├── __init__.py
│   │       ├── state.py            # .dinbutler/ state (~80 LOC)
│   │       └── output.py           # JSON/text formatting (~60 LOC)
│   │
│   ├── sandbox_mcp/                # MCP Server
│   │   ├── __init__.py
│   │   ├── server.py               # FastMCP with 19 tools (~450 LOC)
│   │   └── config.py               # Server config (~40 LOC)
│   │
│   └── sandbox_workflows/          # Parallel Agent Forks (obox)
│       ├── __init__.py
│       ├── main.py                 # obox CLI entry (~80 LOC)
│       ├── commands/
│       │   └── fork.py             # Fork orchestration (~150 LOC)
│       ├── modules/
│       │   ├── agents.py           # SandboxForkAgent (~300 LOC)
│       │   ├── forks.py            # Parallel execution (~200 LOC)
│       │   ├── hooks.py            # Security hooks (~150 LOC)
│       │   ├── logs.py             # Thread-safe logging (~100 LOC)
│       │   └── constants.py        # Configuration (~30 LOC)
│       └── prompts/
│           └── system_prompt.md    # Agent system prompt (~100 lines)
│
├── .claude/                        # Claude Code integration
│   └── commands/
│       ├── prime.md                # General priming (~50 lines)
│       ├── prime_sandbox.md        # Sandbox workflow (~80 lines)
│       └── prime_obox.md           # Parallel fork workflow (~60 lines)
│
├── docs/
│   └── plans/
│       └── claude-code-integration.md  # This plan (copy)
│
├── .mcp.json.sample                # MCP config template
└── pyproject.toml                  # Updated with new entry points
```

## Component 1: CLI (`apps/sandbox_cli/`)

### Commands

**Root Commands:**
- `sbx init [--template] [--timeout] [--envs]` - Create sandbox, save ID to `.dinbutler/`
- `sbx cleanup` - Kill all sandboxes, clear state
- `sbx version` - Show version

**Sandbox Group (`sbx sandbox`):**
- `create` - Create new sandbox
- `connect <id>` - Connect to existing
- `kill <id>` - Kill sandbox
- `info <id>` - Get detailed info
- `status <id>` - Check if running
- `list` - List all sandboxes
- `get-host <id>` - Get container hostname

**Files Group (`sbx files`):**
- `ls <id> <path>` - List directory
- `read <id> <path>` - Read file
- `write <id> <path> <content>` - Write file
- `exists <id> <path>` - Check existence
- `remove <id> <path>` - Delete file/dir
- `mkdir <id> <path>` - Create directory
- `info <id> <path>` - Get file metadata
- `rename <id> <old> <new>` - Move/rename
- `upload <id> <local> <remote>` - Upload file
- `download <id> <remote> <local>` - Download file

**Exec Group (`sbx exec`):**
- `run <id> <command> [--shell] [--cwd] [--root] [--env] [--timeout] [--background]`

### State Management (`.dinbutler/`)
```
.dinbutler/
├── sandbox_id          # Current active sandbox ID
└── config.json         # Optional local config
```

### Estimated LOC: ~790

## Component 2: MCP Server (`apps/sandbox_mcp/`)

### 19 MCP Tools

| # | Tool | CLI Command |
|---|------|-------------|
| 1 | `init_sandbox` | `sbx init` |
| 2 | `create_sandbox` | `sbx sandbox create` |
| 3 | `connect_sandbox` | `sbx sandbox connect` |
| 4 | `kill_sandbox` | `sbx sandbox kill` |
| 5 | `get_sandbox_info` | `sbx sandbox info` |
| 6 | `check_sandbox_status` | `sbx sandbox status` |
| 7 | `list_sandboxes` | `sbx sandbox list` |
| 8 | `list_files` | `sbx files ls` |
| 9 | `read_file` | `sbx files read` |
| 10 | `write_file` | `sbx files write` |
| 11 | `file_exists` | `sbx files exists` |
| 12 | `get_file_info` | `sbx files info` |
| 13 | `remove_file` | `sbx files remove` |
| 14 | `create_directory` | `sbx files mkdir` |
| 15 | `rename_file` | `sbx files rename` |
| 16 | `upload_file` | `sbx files upload` |
| 17 | `download_file` | `sbx files download` |
| 18 | `execute_command` | `sbx exec run` |
| 19 | `sandbox_fork` | Workflow trigger |

### Key Pattern - CLI Wrapper

```python
import subprocess

def run_sbx_cli(args: list[str]) -> str:
    """Execute sbx CLI command and return output."""
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)  # Avoid uv conflicts

    result = subprocess.run(
        ["sbx"] + args,
        capture_output=True,
        text=True,
        env=env
    )
    return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"

@mcp.tool()
def execute_command(sandbox_id: str, command: str, timeout: int = 60) -> str:
    """Run command in sandbox."""
    return run_sbx_cli([
        "exec", "run", sandbox_id, command,
        "--timeout", str(timeout),
        "--json"
    ])
```

### Estimated LOC: ~490

## Component 3: Workflow Engine (`apps/sandbox_workflows/`)

### CLI Usage

```bash
# Run 3 parallel experiments
obox https://github.com/user/repo \
  --branch main \
  --forks 3 \
  --model sonnet \
  --prompt "Add comprehensive tests"

# With prompt file
obox https://github.com/user/repo \
  --prompt prompts/experiment.md
```

### Key Classes

**SandboxForkAgent** - Claude agent for sandbox work:
```python
class SandboxForkAgent:
    def __init__(self, fork_num, repo_url, branch, model, sandbox_id, ...):
        self.client = Anthropic()
        self.system_prompt = self._load_system_prompt()
        self.hooks = HookManager(allowed_paths=[...])

    async def run(self, prompt: str, max_turns: int = 100):
        # Execute agent loop with tool use
```

**HookManager** - Security controls:
```python
class HookManager:
    def validate_tool(self, tool_name: str, args: dict) -> bool:
        # Pre-tool security validation

    def log_result(self, tool_name: str, result: Any):
        # Post-tool logging
```

**Fork Execution** - Parallel orchestration:
```python
def run_forks_parallel(repo, branch, prompt, num_forks, ...):
    with ThreadPoolExecutor(max_workers=num_forks) as executor:
        futures = [executor.submit(run_single_fork, ...) for i in range(num_forks)]
        return [f.result() for f in futures]
```

### Estimated LOC: ~1,110

## Component 4: Claude Integration (`.claude/commands/`)

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/prime` | General DinButler priming |
| `/prime_sandbox` | MCP sandbox tools reference |
| `/prime_obox` | Parallel fork workflow guide |

### Estimated LOC: ~190

## Configuration Files

### `.mcp.json.sample`
```json
{
  "mcpServers": {
    "dinbutler": {
      "command": "uv",
      "args": ["run", "python", "-m", "apps.sandbox_mcp.server"],
      "cwd": "/Users/amund/dinbutler",
      "env": {}
    }
  }
}
```

### `pyproject.toml` Updates
```toml
[project.optional-dependencies]
cli = ["click>=8.1.0", "rich>=13.0.0"]
mcp = ["mcp>=1.0.0"]
workflows = ["anthropic>=0.39.0", "click>=8.1.0"]
all = ["dinbutler[cli,mcp,workflows]"]

[project.scripts]
dinbutler = "dinbutler.cli:main"
sbx = "apps.sandbox_cli.main:cli"
obox = "apps.sandbox_workflows.main:cli"
```

## Implementation Phases

### Phase 1: CLI Layer (Day 1)
1. Create `apps/sandbox_cli/` structure
2. Implement state management (`.dinbutler/`)
3. Implement sandbox commands
4. Implement files commands
5. Implement exec commands
6. Test CLI standalone

### Phase 2: MCP Server (Day 1-2)
1. Create `apps/sandbox_mcp/` structure
2. Implement FastMCP server with CLI wrapper
3. Add all 19 tools
4. Test with Claude Code

### Phase 3: Claude Integration (Day 2)
1. Create `.claude/commands/` slash commands
2. Create `.mcp.json.sample`
3. Update pyproject.toml
4. Test full integration

### Phase 4: Workflow Engine (Day 2-3)
1. Create `apps/sandbox_workflows/` structure
2. Implement logging system
3. Implement hook system
4. Implement SandboxForkAgent
5. Implement parallel fork execution
6. Test obox command

### Phase 5: Documentation & Polish (Day 3-4)
1. Copy this plan to `docs/plans/`
2. Update README with MCP usage
3. Add tests
4. Final integration testing

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| click | >=8.1.0 | CLI framework |
| rich | >=13.0.0 | Terminal formatting |
| mcp | >=1.0.0 | MCP server (FastMCP) |
| anthropic | >=0.39.0 | Claude SDK for workflows |

## LOC Summary

| Component | Lines |
|-----------|-------|
| CLI (`apps/sandbox_cli/`) | ~790 |
| MCP Server (`apps/sandbox_mcp/`) | ~490 |
| Workflows (`apps/sandbox_workflows/`) | ~1,110 |
| Claude Integration (`.claude/`) | ~190 |
| Configuration | ~50 |
| **Total** | **~2,630** |

## Critical Files to Modify

1. `/Users/amund/dinbutler/pyproject.toml` - Add entry points and deps
2. `/Users/amund/dinbutler/dinbutler/sandbox.py` - Reference for SDK patterns
3. `/Users/amund/dinbutler/dinbutler/services/commands.py` - Command execution patterns
4. `/Users/amund/dinbutler/dinbutler/services/filesystem.py` - File operation patterns

## Success Criteria

1. ✅ `sbx` CLI works standalone with all commands
2. ✅ MCP server registers with Claude Code via `.mcp.json`
3. ✅ All 19 MCP tools functional
4. ✅ `obox` runs parallel fork experiments
5. ✅ Slash commands prime Claude for sandbox work
6. ✅ Security hooks prevent dangerous operations
