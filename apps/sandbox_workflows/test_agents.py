"""
Quick test script for SandboxForkAgent and parallel fork execution.

Usage:
    python test_agents.py
"""

import asyncio
from pathlib import Path
from modules.agents import SandboxForkAgent
from modules.forks import run_forks_parallel, print_results_summary
from modules.logs import setup_logging


async def test_single_agent():
    """Test single agent execution."""
    print("=" * 80)
    print("Testing SandboxForkAgent")
    print("=" * 80)

    agent = SandboxForkAgent(
        fork_num=0,
        sandbox_id="test_sandbox_001",
        repo_url="https://github.com/test/repo",
        branch="main",
        model="sonnet",
        sandbox_root=Path.cwd(),
    )

    # Simple test task
    task = "List all Python files in the current directory using Glob."

    result = await agent.run(task, max_turns=5)

    print(f"\nSuccess: {result['success']}")
    print(f"Turns: {result['turns']}")
    print(f"Tool calls: {result['tool_calls']}")
    print(f"Errors: {result['errors']}")
    print(f"Tokens: {result['total_tokens']}")
    print(f"Cost: ${result['total_cost']:.4f}")
    print(f"\nFinal response:\n{result['final_response']}")


def test_parallel_forks():
    """Test parallel fork execution."""
    print("\n" + "=" * 80)
    print("Testing Parallel Fork Execution")
    print("=" * 80)

    # Simple task for all forks
    task = "Create a file called 'hello.txt' with the text 'Hello from fork {fork_num}'."

    results = run_forks_parallel(
        repo_url="https://github.com/test/repo",
        branch="main",
        prompt=task,
        num_forks=3,
        model="sonnet",
        max_turns=5,
        log_dir="./test_logs",
    )

    # Print summary
    print_results_summary(results)


def main():
    """Run all tests."""
    # Setup logging
    setup_logging(verbose=True)

    print("\nDinButler Sandbox Agent Tests")
    print("=" * 80)

    # Test 1: Single agent
    print("\n[1/2] Testing single agent...")
    try:
        asyncio.run(test_single_agent())
        print("\n✓ Single agent test passed")
    except Exception as e:
        print(f"\n✗ Single agent test failed: {e}")

    # Test 2: Parallel forks
    print("\n[2/2] Testing parallel forks...")
    try:
        test_parallel_forks()
        print("\n✓ Parallel forks test passed")
    except Exception as e:
        print(f"\n✗ Parallel forks test failed: {e}")

    print("\n" + "=" * 80)
    print("Tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
