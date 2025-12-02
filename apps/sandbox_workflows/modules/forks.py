"""
Fork execution orchestration.

Manages parallel execution of multiple agent forks with proper resource
management, logging, and error handling.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from pathlib import Path

from apps.sandbox_workflows.modules.agents import SandboxForkAgent
from apps.sandbox_workflows.modules.logs import ForkLogger, ProgressTracker
from apps.sandbox_workflows.modules.hooks import HookManager
from apps.sandbox_workflows.modules.constants import (
    MAX_FORKS,
    DEFAULT_MODEL,
    MAX_AGENT_TURNS,
    THREAD_POOL_MAX_WORKERS,
    DEFAULT_LOG_DIR,
)

logger = logging.getLogger(__name__)


class ForkExecutionError(Exception):
    """Raised when fork execution fails."""
    pass


def run_single_fork(
    fork_num: int,
    sandbox_id: str,
    repo_url: str,
    branch: str,
    prompt: str,
    model: str,
    max_turns: int,
    fork_logger: ForkLogger,
    progress_tracker: Optional[ProgressTracker] = None,
    sandbox_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run a single fork in its own thread with asyncio event loop.

    Each fork gets its own event loop to allow async operations while
    maintaining thread-based parallelism for the overall orchestration.

    Args:
        fork_num: Fork number (0-indexed)
        sandbox_id: Unique sandbox identifier
        repo_url: Git repository URL
        branch: Git branch name
        prompt: Task prompt for the agent
        model: Claude model to use
        max_turns: Maximum agent turns
        fork_logger: Logger instance for this fork
        progress_tracker: Optional progress tracker
        sandbox_root: Root directory for the sandbox

    Returns:
        Dictionary with fork execution results:
        - fork_num: Fork number
        - sandbox_id: Sandbox ID
        - success: Whether execution succeeded
        - final_response: Agent's final response
        - turns: Number of turns taken
        - tool_calls: Total tool calls made
        - errors: Number of errors encountered
        - total_tokens: Total tokens used
        - total_cost: Estimated cost in USD
        - execution_time: Execution time in seconds
        - error: Error message (if failed)
    """
    start_time = time.time()

    if progress_tracker:
        progress_tracker.start_fork()

    fork_logger.log(fork_num, f"Starting fork {fork_num} in sandbox {sandbox_id}", "info")
    fork_logger.log(fork_num, f"Repository: {repo_url} (branch: {branch})", "info")
    fork_logger.log(fork_num, f"Model: {model}, Max turns: {max_turns}", "info")

    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Initialize agent
            agent = SandboxForkAgent(
                fork_num=fork_num,
                sandbox_id=sandbox_id,
                repo_url=repo_url,
                branch=branch,
                model=model,
                logger_instance=fork_logger,
                sandbox_root=sandbox_root,
            )

            # Run agent
            result = loop.run_until_complete(agent.run(prompt, max_turns=max_turns))

            # Add fork metadata
            execution_time = time.time() - start_time
            result.update({
                "fork_num": fork_num,
                "sandbox_id": sandbox_id,
                "execution_time": execution_time,
            })

            # Log completion
            status = "SUCCESS" if result["success"] else "FAILED"
            fork_logger.log(
                fork_num,
                f"Fork {fork_num} completed: {status} "
                f"(turns={result['turns']}, tools={result['tool_calls']}, "
                f"errors={result['errors']}, time={execution_time:.2f}s)",
                "info" if result["success"] else "error"
            )

            if progress_tracker:
                progress_tracker.complete_fork(result["success"])

            return result

        finally:
            # Clean up event loop
            loop.close()

    except Exception as e:
        # Handle unexpected errors
        execution_time = time.time() - start_time
        error_msg = f"Fork {fork_num} failed with exception: {str(e)}"

        fork_logger.log(fork_num, error_msg, "error")

        if progress_tracker:
            progress_tracker.complete_fork(False)

        return {
            "fork_num": fork_num,
            "sandbox_id": sandbox_id,
            "success": False,
            "final_response": "",
            "turns": 0,
            "tool_calls": 0,
            "errors": 1,
            "total_tokens": 0,
            "total_cost": 0.0,
            "execution_time": execution_time,
            "error": str(e),
        }


def run_forks_parallel(
    repo_url: str,
    branch: str,
    prompt: str,
    num_forks: int,
    sandbox_ids: Optional[List[str]] = None,
    model: str = DEFAULT_MODEL,
    max_turns: int = MAX_AGENT_TURNS,
    log_dir: Optional[str] = None,
    sandbox_roots: Optional[List[Path]] = None,
    max_workers: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Run multiple forks in parallel using ThreadPoolExecutor.

    Each fork runs in its own thread with its own async event loop,
    allowing for true parallelism across multiple Claude API calls.

    Args:
        repo_url: Git repository URL
        branch: Git branch name
        prompt: Task prompt for all agents
        num_forks: Number of parallel forks to run
        sandbox_ids: List of sandbox IDs (one per fork, or None to generate)
        model: Claude model to use (default: sonnet)
        max_turns: Maximum agent turns per fork (default: 100)
        log_dir: Directory for log files (default: ./logs)
        sandbox_roots: List of sandbox root directories (one per fork)
        max_workers: Maximum worker threads (default: THREAD_POOL_MAX_WORKERS)

    Returns:
        List of fork execution results (one per fork)

    Raises:
        ValueError: If invalid parameters provided
        ForkExecutionError: If execution fails critically
    """
    # Validate inputs
    if num_forks < 1:
        raise ValueError("num_forks must be at least 1")
    if num_forks > MAX_FORKS:
        raise ValueError(f"num_forks exceeds maximum of {MAX_FORKS}")

    if sandbox_ids and len(sandbox_ids) != num_forks:
        raise ValueError(f"sandbox_ids length ({len(sandbox_ids)}) must match num_forks ({num_forks})")

    if sandbox_roots and len(sandbox_roots) != num_forks:
        raise ValueError(f"sandbox_roots length ({len(sandbox_roots)}) must match num_forks ({num_forks})")

    # Generate sandbox IDs if not provided
    if not sandbox_ids:
        import uuid
        sandbox_ids = [f"fork_{i}_{uuid.uuid4().hex[:8]}" for i in range(num_forks)]

    # Use current directory as sandbox root if not provided
    if not sandbox_roots:
        sandbox_roots = [Path.cwd() for _ in range(num_forks)]

    # Initialize logging
    log_path = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    fork_logger = ForkLogger(log_path)

    # Initialize progress tracker
    progress_tracker = ProgressTracker(num_forks)

    logger.info(f"Starting {num_forks} parallel forks")
    logger.info(f"Repository: {repo_url} (branch: {branch})")
    logger.info(f"Model: {model}, Max turns: {max_turns}")
    logger.info(f"Log directory: {log_path}")

    # Determine number of workers
    workers = max_workers if max_workers else min(num_forks, THREAD_POOL_MAX_WORKERS)

    logger.info(f"Using {workers} worker threads")

    start_time = time.time()
    results = []

    try:
        # Create thread pool and submit all forks
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all fork tasks
            future_to_fork = {}
            for fork_num in range(num_forks):
                future = executor.submit(
                    run_single_fork,
                    fork_num=fork_num,
                    sandbox_id=sandbox_ids[fork_num],
                    repo_url=repo_url,
                    branch=branch,
                    prompt=prompt,
                    model=model,
                    max_turns=max_turns,
                    fork_logger=fork_logger,
                    progress_tracker=progress_tracker,
                    sandbox_root=sandbox_roots[fork_num],
                )
                future_to_fork[future] = fork_num

            # Collect results as they complete
            for future in as_completed(future_to_fork):
                fork_num = future_to_fork[future]
                try:
                    result = future.result()
                    results.append(result)

                    # Log progress
                    status = progress_tracker.get_status()
                    logger.info(
                        f"Fork {fork_num} completed "
                        f"({status['completed'] + status['failed']}/{num_forks} done, "
                        f"{status['in_progress']} in progress)"
                    )

                except Exception as e:
                    logger.error(f"Fork {fork_num} raised exception: {e}")
                    # Create error result
                    results.append({
                        "fork_num": fork_num,
                        "sandbox_id": sandbox_ids[fork_num],
                        "success": False,
                        "final_response": "",
                        "turns": 0,
                        "tool_calls": 0,
                        "errors": 1,
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "execution_time": 0.0,
                        "error": str(e),
                    })

        # Sort results by fork number
        results.sort(key=lambda x: x["fork_num"])

        # Calculate summary statistics
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r["success"])
        failed = num_forks - successful
        total_turns = sum(r["turns"] for r in results)
        total_tool_calls = sum(r["tool_calls"] for r in results)
        total_tokens = sum(r["total_tokens"] for r in results)
        total_cost = sum(r["total_cost"] for r in results)

        # Log summary
        logger.info("=" * 80)
        logger.info("FORK EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total forks: {num_forks}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total execution time: {total_time:.2f}s")
        logger.info(f"Average time per fork: {total_time / num_forks:.2f}s")
        logger.info(f"Total agent turns: {total_turns}")
        logger.info(f"Total tool calls: {total_tool_calls}")
        logger.info(f"Total tokens: {total_tokens:,}")
        logger.info(f"Total cost: ${total_cost:.4f}")
        logger.info("=" * 80)

        # Write summary to each fork's log
        for fork_num in range(num_forks):
            fork_logger.log(fork_num, "=" * 60, "info")
            fork_logger.log(fork_num, "EXECUTION SUMMARY", "info")
            fork_logger.log(fork_num, "=" * 60, "info")
            result = results[fork_num]
            fork_logger.log(fork_num, f"Success: {result['success']}", "info")
            fork_logger.log(fork_num, f"Turns: {result['turns']}", "info")
            fork_logger.log(fork_num, f"Tool calls: {result['tool_calls']}", "info")
            fork_logger.log(fork_num, f"Errors: {result['errors']}", "info")
            fork_logger.log(fork_num, f"Tokens: {result['total_tokens']:,}", "info")
            fork_logger.log(fork_num, f"Cost: ${result['total_cost']:.4f}", "info")
            fork_logger.log(fork_num, f"Execution time: {result['execution_time']:.2f}s", "info")
            if not result["success"] and "error" in result:
                fork_logger.log(fork_num, f"Error: {result['error']}", "error")
            fork_logger.log(fork_num, "=" * 60, "info")

        return results

    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
        raise

    except Exception as e:
        logger.error(f"Fork execution failed: {e}")
        raise ForkExecutionError(f"Parallel execution failed: {str(e)}") from e

    finally:
        # Clean up logging
        fork_logger.close_all()


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate results from multiple forks into a summary.

    Args:
        results: List of fork execution results

    Returns:
        Aggregated summary with statistics and insights
    """
    num_forks = len(results)
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    return {
        "total_forks": num_forks,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / num_forks if num_forks > 0 else 0.0,
        "total_turns": sum(r["turns"] for r in results),
        "total_tool_calls": sum(r["tool_calls"] for r in results),
        "total_errors": sum(r["errors"] for r in results),
        "total_tokens": sum(r["total_tokens"] for r in results),
        "total_cost": sum(r["total_cost"] for r in results),
        "total_time": sum(r["execution_time"] for r in results),
        "avg_turns": sum(r["turns"] for r in results) / num_forks if num_forks > 0 else 0.0,
        "avg_tool_calls": sum(r["tool_calls"] for r in results) / num_forks if num_forks > 0 else 0.0,
        "avg_time": sum(r["execution_time"] for r in results) / num_forks if num_forks > 0 else 0.0,
        "avg_cost": sum(r["total_cost"] for r in results) / num_forks if num_forks > 0 else 0.0,
        "successful_forks": [r["fork_num"] for r in successful],
        "failed_forks": [r["fork_num"] for r in failed],
    }


def print_results_summary(results: List[Dict[str, Any]]) -> None:
    """
    Print a human-readable summary of fork results.

    Args:
        results: List of fork execution results
    """
    summary = aggregate_results(results)

    print("\n" + "=" * 80)
    print("FORK EXECUTION RESULTS")
    print("=" * 80)
    print(f"Total forks:       {summary['total_forks']}")
    print(f"Successful:        {summary['successful']} ({summary['success_rate']*100:.1f}%)")
    print(f"Failed:            {summary['failed']}")
    print()
    print(f"Total turns:       {summary['total_turns']}")
    print(f"Total tool calls:  {summary['total_tool_calls']}")
    print(f"Total errors:      {summary['total_errors']}")
    print(f"Total tokens:      {summary['total_tokens']:,}")
    print(f"Total cost:        ${summary['total_cost']:.4f}")
    print(f"Total time:        {summary['total_time']:.2f}s")
    print()
    print(f"Avg turns/fork:    {summary['avg_turns']:.1f}")
    print(f"Avg tools/fork:    {summary['avg_tool_calls']:.1f}")
    print(f"Avg time/fork:     {summary['avg_time']:.2f}s")
    print(f"Avg cost/fork:     ${summary['avg_cost']:.4f}")
    print("=" * 80)

    if summary["failed"] > 0:
        print("\nFailed forks:")
        for result in results:
            if not result["success"]:
                error = result.get("error", "Unknown error")
                print(f"  Fork {result['fork_num']}: {error}")
        print()
