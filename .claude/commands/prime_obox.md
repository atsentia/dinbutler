# DinButler Obox - Parallel Fork Workflow

Obox (Orchestration Box) enables running multiple Claude agents in parallel, each experimenting with the same codebase in isolated sandboxes.

## What is Obox?

Obox is DinButler's parallel execution framework that:

- Forks a codebase into N isolated sandboxes
- Runs different Claude agents in each sandbox
- Each agent experiments independently without conflicts
- Aggregates results for comparison
- Automatically cleans up resources

**Use cases:**
- Testing multiple bug fix approaches simultaneously
- Comparing different refactoring strategies
- Parallel feature development experiments
- A/B testing code changes
- Exploring solution space efficiently

## Core Concepts

### Fork Workflow

```
Original Codebase
       |
       v
   [Obox Fork]
       |
       +----> Sandbox 1 (Agent: "fix with regex")
       |
       +----> Sandbox 2 (Agent: "fix with AST parsing")
       |
       +----> Sandbox 3 (Agent: "fix with external lib")
       |
       v
   [Aggregate Results]
       |
       v
   Choose Best Approach
```

### Agent Types

Each sandbox runs a different "agent" - a Claude instance with specific instructions:

- **Exploratory agents** - Try different approaches to same problem
- **Competitive agents** - Race to solve problem fastest
- **Complementary agents** - Work on different parts of codebase
- **Validation agents** - Test code from different angles

## Basic Usage

```python
from dinbutler import Obox

# Define the experiment
obox = Obox.create(
    base_path="/path/to/codebase",
    num_forks=3,
    template="python"
)

# Fork codebase into 3 sandboxes
sandboxes = obox.fork()

# Define agent tasks (different approaches)
agents = [
    {"id": "agent_1", "task": "Fix bug using regex"},
    {"id": "agent_2", "task": "Fix bug using AST parsing"},
    {"id": "agent_3", "task": "Fix bug using external library"}
]

# Run agents in parallel
results = obox.run_parallel(agents, timeout=300)

# Compare results
for agent_id, result in results.items():
    print(f"{agent_id}: {result['success']}")
    print(f"  Output: {result['stdout']}")
    print(f"  Time: {result['duration']}s")

# Select best result
best = obox.select_best(results, criteria="fastest")

# Apply winning changes back to original codebase
obox.merge_changes(best['sandbox_id'], target="/path/to/codebase")

# Cleanup all sandboxes
obox.cleanup()
```

## Advanced Patterns

### Pattern 1: Parallel Refactoring

```python
obox = Obox.create(base_path="/app/legacy_code", num_forks=4)
sandboxes = obox.fork()

agents = [
    {
        "id": "modern_python",
        "task": "Refactor to Python 3.11+ features (match/case, type hints)",
        "test_command": "pytest tests/"
    },
    {
        "id": "async_io",
        "task": "Convert to async/await for I/O operations",
        "test_command": "pytest tests/"
    },
    {
        "id": "dataclasses",
        "task": "Replace classes with dataclasses/pydantic",
        "test_command": "pytest tests/"
    },
    {
        "id": "functional",
        "task": "Refactor to functional programming style",
        "test_command": "pytest tests/"
    }
]

# Run all refactorings in parallel
results = obox.run_parallel(agents, timeout=600)

# Filter to only successful refactorings (tests pass)
passing = {k: v for k, v in results.items() if v['tests_passed']}

# Compare performance
for agent_id, result in passing.items():
    print(f"{agent_id}:")
    print(f"  Test time: {result['test_duration']}s")
    print(f"  Lines changed: {result['diff_stats']['lines_changed']}")
```

### Pattern 2: Competitive Bug Fixing

```python
obox = Obox.create(base_path="/app/buggy_code", num_forks=5)
sandboxes = obox.fork()

# Same task, different agents race to solve
bug_description = "Fix memory leak in request handler"

agents = [
    {"id": f"agent_{i}", "task": bug_description, "approach": "freestyle"}
    for i in range(5)
]

# Run with timeout - first to succeed wins
results = obox.run_competitive(agents, timeout=300)

# Winner is first to pass tests
winner = results['winner']
print(f"Winner: {winner['id']} in {winner['duration']}s")
print(f"Approach: {winner['summary']}")

# Apply winning fix
obox.merge_changes(winner['sandbox_id'])
```

### Pattern 3: Multi-Stage Pipeline

```python
obox = Obox.create(base_path="/app/project", num_forks=3)

# Stage 1: Parallel feature exploration
stage1_agents = [
    {"id": "auth_jwt", "task": "Add JWT authentication"},
    {"id": "auth_oauth", "task": "Add OAuth2 authentication"},
    {"id": "auth_session", "task": "Add session-based auth"}
]

stage1_results = obox.run_parallel(stage1_agents, timeout=300)

# Select best approach from stage 1
best_auth = obox.select_best(stage1_results, criteria="test_coverage")

# Stage 2: Build on winning approach
obox.reset_to(best_auth['sandbox_id'])
obox.fork(num_forks=3)

stage2_agents = [
    {"id": "add_rate_limit", "task": "Add rate limiting"},
    {"id": "add_2fa", "task": "Add two-factor auth"},
    {"id": "add_rbac", "task": "Add role-based access control"}
]

stage2_results = obox.run_parallel(stage2_agents, timeout=300)

# Merge all stage 2 features
obox.merge_all(stage2_results)
```

### Pattern 4: Code Quality Comparison

```python
obox = Obox.create(base_path="/app/messy_code", num_forks=1)
sandboxes = obox.fork()

# Single agent, multiple quality metrics
agent_task = "Improve code quality across all files"

result = obox.run_single(
    agent={"id": "quality_agent", "task": agent_task},
    metrics=[
        {"name": "pylint", "command": "pylint --score-only src/"},
        {"name": "mypy", "command": "mypy src/"},
        {"name": "complexity", "command": "radon cc src/ -a"},
        {"name": "coverage", "command": "pytest --cov=src tests/"}
    ]
)

# Compare before/after metrics
print("Quality improvements:")
for metric, scores in result['metrics'].items():
    print(f"  {metric}: {scores['before']} -> {scores['after']}")
```

## Obox API Reference

### Core Methods

```python
# Create orchestration box
obox = Obox.create(
    base_path="/path/to/code",
    num_forks=3,
    template="python",
    metadata={"experiment": "refactor_v1"}
)

# Fork codebase into N sandboxes
sandboxes = obox.fork()  # Returns list of sandbox IDs

# Run agents in parallel
results = obox.run_parallel(
    agents=[...],
    timeout=300,
    fail_fast=False  # Continue even if one fails
)

# Run competitive mode (first to succeed wins)
results = obox.run_competitive(
    agents=[...],
    timeout=300
)

# Select best result by criteria
best = obox.select_best(
    results,
    criteria="fastest" | "most_tests" | "least_changes" | custom_fn
)

# Merge changes from winning sandbox
obox.merge_changes(
    sandbox_id="sandbox_abc123",
    target="/path/to/original"
)

# Cleanup all sandboxes
obox.cleanup()
```

### Agent Definition Schema

```python
agent = {
    "id": "unique_agent_id",           # Required: Agent identifier
    "task": "Task description",         # Required: What to do
    "approach": "optional strategy",    # Optional: How to do it
    "test_command": "pytest tests/",   # Optional: Validation command
    "success_criteria": lambda r: ..., # Optional: Custom success check
    "timeout": 300                      # Optional: Override default
}
```

### Result Schema

```python
result = {
    "agent_id": "agent_1",
    "sandbox_id": "sandbox_abc123",
    "success": True,
    "exit_code": 0,
    "stdout": "...",
    "stderr": "...",
    "duration": 42.5,  # seconds
    "tests_passed": True,
    "test_output": "...",
    "diff_stats": {
        "files_changed": 5,
        "lines_added": 120,
        "lines_removed": 80
    },
    "metrics": {...}  # Custom metrics if provided
}
```

## Real-World Example: API Redesign

```python
from dinbutler import Obox

# Experiment: Redesign REST API for better performance
obox = Obox.create(
    base_path="/app/api_server",
    num_forks=4,
    template="python"
)

sandboxes = obox.fork()

agents = [
    {
        "id": "graphql",
        "task": "Convert REST to GraphQL API",
        "test_command": "pytest tests/ && locust -f load_test.py --headless",
        "success_criteria": lambda r: r['tests_passed'] and r['p95_latency'] < 100
    },
    {
        "id": "grpc",
        "task": "Convert REST to gRPC API",
        "test_command": "pytest tests/ && ghz --insecure --proto api.proto",
        "success_criteria": lambda r: r['tests_passed'] and r['rps'] > 1000
    },
    {
        "id": "async_rest",
        "task": "Keep REST but make async with FastAPI",
        "test_command": "pytest tests/ && ab -n 10000 -c 100",
        "success_criteria": lambda r: r['tests_passed'] and r['requests_per_sec'] > 800
    },
    {
        "id": "optimize_rest",
        "task": "Optimize existing REST (caching, connection pooling, etc)",
        "test_command": "pytest tests/ && wrk -t12 -c400 -d30s",
        "success_criteria": lambda r: r['tests_passed'] and r['latency_avg'] < 50
    }
]

# Run all approaches in parallel
results = obox.run_parallel(agents, timeout=900)

# Filter to successful implementations
successful = {k: v for k, v in results.items() if v['success']}

# Compare performance metrics
print("Performance comparison:")
for agent_id, result in successful.items():
    print(f"\n{agent_id}:")
    print(f"  Latency (p95): {result['p95_latency']}ms")
    print(f"  Throughput: {result['requests_per_sec']} req/s")
    print(f"  Lines changed: {result['diff_stats']['lines_changed']}")
    print(f"  Tests passing: {result['tests_passed']}")

# Select based on composite score
def score_api(result):
    # Lower latency + higher throughput + fewer changes = better
    return (
        (100 - result['p95_latency']) * 0.4 +
        (result['requests_per_sec'] / 10) * 0.4 +
        (1000 - result['diff_stats']['lines_changed']) * 0.2
    )

best = max(successful.items(), key=lambda x: score_api(x[1]))
print(f"\nBest approach: {best[0]} (score: {score_api(best[1])})")

# Apply winning API design
obox.merge_changes(best[1]['sandbox_id'])
obox.cleanup()
```

## Best Practices

1. **Define clear success criteria** - Automated tests, performance targets, quality metrics
2. **Use timeouts generously** - Parallel tasks may take longer than sequential
3. **Monitor resource usage** - N sandboxes = N * resources
4. **Always cleanup** - Use try/finally to ensure sandbox cleanup
5. **Start small** - Test with 2-3 forks before scaling to 10+
6. **Log everything** - Parallel debugging is harder, comprehensive logs help

## Limitations

- **Resource intensive** - Each fork is a full Docker container
- **Not for production** - Experimental workflow only
- **Network isolated** - Sandboxes can't communicate with each other
- **Manual merge** - Winning changes must be manually reviewed before merging

## When to Use Obox vs Sequential Claude

**Use Obox when:**
- Multiple valid approaches exist
- Solution space is large and uncertain
- Time > cost (pay for parallelism)
- Experimentation is valuable

**Use sequential Claude when:**
- Clear optimal path exists
- Resource constrained
- Single agent is sufficient
- Iterative refinement preferred

For basic sandbox usage, see `/prime` and `/prime_sandbox`.
