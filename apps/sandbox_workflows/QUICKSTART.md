# SandboxForkAgent - Quick Start Guide

## Installation

No additional dependencies needed - uses existing DinButler infrastructure.

Requires:
- `anthropic` Python SDK (for Claude API)
- `ANTHROPIC_API_KEY` environment variable

## 5-Minute Quick Start

### 1. Single Agent Execution

```python
import asyncio
from pathlib import Path
from modules.agents import SandboxForkAgent

async def main():
    agent = SandboxForkAgent(
        fork_num=0,
        sandbox_id="test_sandbox",
        model="sonnet",
        sandbox_root=Path.cwd(),
    )

    result = await agent.run(
        task_prompt="List all Python files in this directory",
        max_turns=10,
    )

    print(f"Success: {result['success']}")
    print(f"Cost: ${result['total_cost']:.4f}")
    print(f"Response:\n{result['final_response']}")

asyncio.run(main())
```

### 2. Parallel Fork Execution

```python
from modules.forks import run_forks_parallel, print_results_summary

results = run_forks_parallel(
    repo_url="https://github.com/user/repo",
    branch="main",
    prompt="Analyze this codebase and suggest improvements",
    num_forks=3,
    model="sonnet",
    max_turns=50,
)

print_results_summary(results)
```

### 3. With Real Sandboxes

```python
from dinbutler import Sandbox
from modules.forks import run_forks_parallel

# Create sandboxes
sandboxes = [Sandbox.create(template="python") for _ in range(5)]
sandbox_ids = [sb.sandbox_id for sb in sandboxes]

# Run experiments
results = run_forks_parallel(
    repo_url="https://github.com/user/repo",
    branch="main",
    prompt="Run unit tests with different Python versions",
    num_forks=5,
    sandbox_ids=sandbox_ids,
)

# Cleanup
for sb in sandboxes:
    sb.kill()
```

## Key Functions

### `SandboxForkAgent.run()`
Execute agent with a task prompt.

**Returns:**
```python
{
    "success": True,
    "final_response": "...",
    "turns": 15,
    "tool_calls": 42,
    "errors": 0,
    "total_tokens": 12500,
    "total_cost": 0.0375,
}
```

### `run_forks_parallel()`
Run multiple agents in parallel.

**Parameters:**
- `repo_url` - Git repository URL
- `branch` - Git branch name
- `prompt` - Task for all agents
- `num_forks` - Number of parallel forks
- `model` - Claude model ("sonnet", "opus", "haiku")
- `max_turns` - Max turns per agent

**Returns:** List of result dicts (one per fork)

## Available Tools

Agents can use these tools automatically:

1. **Bash** - Execute shell commands
2. **Read** - Read file contents
3. **Write** - Create/overwrite files
4. **Edit** - Replace text in files
5. **Glob** - Find files by pattern
6. **Grep** - Search file contents

## Security

All operations are validated:

- Path validation (only allowed directories)
- Command blocking (dangerous commands rejected)
- Size limits (100MB max file size)
- Resource limits (50 tools/turn, 100 turns max)

## Logging

Per-fork logs are automatically created:

```
logs/fork_0_20251202_143022.log
logs/fork_1_20251202_143022.log
logs/fork_2_20251202_143022.log
```

Each log contains:
- Agent turns
- Tool calls with parameters
- Results or errors
- Execution summary

## Model Selection

```python
# Fast & cheap
model="haiku"  # $1 per million tokens

# Balanced (default)
model="sonnet"  # $3 per million tokens

# Most capable
model="opus"  # $15 per million tokens
```

## Common Patterns

### Experiment with Multiple Approaches

```python
results = run_forks_parallel(
    repo_url="...",
    branch="main",
    prompt="Implement feature X. Try a different approach in each fork.",
    num_forks=5,
)

# Compare results
for r in results:
    print(f"Fork {r['fork_num']}: {r['final_response'][:100]}...")
```

### Distributed Testing

```python
test_commands = [
    "pytest tests/unit/",
    "pytest tests/integration/",
    "pytest tests/e2e/",
]

results = []
for i, cmd in enumerate(test_commands):
    result = run_forks_parallel(
        repo_url="...",
        branch="main",
        prompt=f"Run: {cmd}",
        num_forks=1,
    )
    results.extend(result)
```

### A/B Testing

```python
prompts = [
    "Implement feature X using approach A",
    "Implement feature X using approach B",
]

all_results = []
for prompt in prompts:
    results = run_forks_parallel(
        repo_url="...",
        branch="main",
        prompt=prompt,
        num_forks=3,
    )
    all_results.extend(results)
```

## Troubleshooting

### API Key Not Set
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

### Import Errors
```bash
cd /Users/amund/dinbutler/apps/sandbox_workflows
python -c "from modules.agents import SandboxForkAgent"
```

### Security Violations
Check logs for blocked operations:
```bash
grep "SECURITY VIOLATION" logs/fork_*.log
```

### Tool Execution Failures
Enable verbose logging:
```python
from modules.logs import setup_logging
setup_logging(verbose=True)
```

## Testing

Run the test suite:
```bash
cd /Users/amund/dinbutler/apps/sandbox_workflows
python test_agents.py
```

Expected output:
- Single agent test passes
- Parallel fork test passes (3 forks)
- Logs created in `./test_logs/`

## Performance Tips

1. **Use Haiku for speed** - 2-3x faster than Sonnet
2. **Limit max_turns** - Prevent runaway agents
3. **Set max_workers** - Respect API rate limits
4. **Pre-create sandboxes** - Reduce initialization overhead
5. **Use specific prompts** - Fewer turns = lower cost

## Cost Estimation

Rough estimates for typical tasks:

| Task | Turns | Tokens | Cost (Sonnet) |
|------|-------|--------|---------------|
| Simple file operation | 2-3 | 2,000 | $0.006 |
| Code analysis | 5-10 | 10,000 | $0.030 |
| Feature implementation | 20-40 | 50,000 | $0.150 |
| Complex debugging | 50-100 | 200,000 | $0.600 |

Multiply by number of forks for parallel execution.

## Further Reading

- **README_AGENTS.md** - Complete documentation
- **modules/agents.py** - Implementation details
- **modules/forks.py** - Orchestration logic
- **modules/hooks.py** - Security implementation
- **modules/constants.py** - Configuration options

## Support

For issues or questions, check the logs first:
```bash
tail -f logs/fork_*.log
```

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

Part of the DinButler project.
