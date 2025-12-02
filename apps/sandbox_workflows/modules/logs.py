"""
Thread-safe logging utilities for parallel fork execution.

Provides per-fork logging with thread safety and structured output.
"""

import logging
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

from .constants import (
    DEFAULT_LOG_DIR,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
)


class ForkLogger:
    """
    Thread-safe logger for parallel fork execution.

    Each fork gets its own log file, and logging operations are
    protected by locks to prevent race conditions.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the fork logger.

        Args:
            log_dir: Directory for log files (defaults to DEFAULT_LOG_DIR)
        """
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Thread-safe storage for fork loggers
        self._loggers: dict[int, logging.Logger] = {}
        self._lock = threading.Lock()

        # Timestamp for this logging session
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_logger(self, fork_id: int) -> logging.Logger:
        """
        Get or create a logger for a specific fork.

        Args:
            fork_id: Unique fork identifier

        Returns:
            Logger instance for the fork
        """
        with self._lock:
            if fork_id not in self._loggers:
                self._loggers[fork_id] = self._create_fork_logger(fork_id)
            return self._loggers[fork_id]

    def _create_fork_logger(self, fork_id: int) -> logging.Logger:
        """
        Create a new logger for a fork.

        Args:
            fork_id: Unique fork identifier

        Returns:
            Configured logger instance
        """
        # Create logger with unique name
        logger_name = f"fork_{fork_id}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # File handler for this fork
        log_file = self.log_dir / f"fork_{fork_id}_{self.session_timestamp}.log"
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Formatter with fork ID
        formatter = logging.Formatter(
            LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        # Add fork_id to logger for format string
        logger = logging.LoggerAdapter(logger, {"fork_id": fork_id})

        return logger

    def log(self, fork_id: int, message: str, level: str = "info") -> None:
        """
        Log a message for a specific fork.

        Args:
            fork_id: Fork identifier
            message: Log message
            level: Log level (debug, info, warning, error, critical)
        """
        logger = self.get_logger(fork_id)

        level_map = {
            "debug": logger.debug,
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
            "critical": logger.critical,
        }

        log_func = level_map.get(level.lower(), logger.info)
        log_func(message)

    def log_tool_call(
        self,
        fork_id: int,
        tool_name: str,
        parameters: dict,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Log a tool call with its parameters and result.

        Args:
            fork_id: Fork identifier
            tool_name: Name of the tool called
            parameters: Tool parameters
            result: Tool call result (if successful)
            error: Error message (if failed)
        """
        logger = self.get_logger(fork_id)

        logger.info(f"Tool call: {tool_name}")
        logger.debug(f"Parameters: {parameters}")

        if error:
            logger.error(f"Tool call failed: {error}")
        elif result:
            logger.debug(f"Result: {result[:500]}...")  # Truncate long results

    def log_agent_turn(
        self,
        fork_id: int,
        turn_number: int,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
    ) -> None:
        """
        Log an agent turn with prompt and response.

        Args:
            fork_id: Fork identifier
            turn_number: Turn number
            prompt: User/system prompt
            response: Agent response
        """
        logger = self.get_logger(fork_id)

        logger.info(f"Turn {turn_number} starting")

        if prompt:
            logger.debug(f"Prompt: {prompt[:200]}...")

        if response:
            logger.debug(f"Response: {response[:200]}...")

    def close_all(self) -> None:
        """
        Close all fork loggers and flush handlers.
        """
        with self._lock:
            for logger in self._loggers.values():
                # LoggerAdapter wraps the actual logger
                if isinstance(logger, logging.LoggerAdapter):
                    actual_logger = logger.logger
                else:
                    actual_logger = logger

                for handler in actual_logger.handlers[:]:
                    handler.flush()
                    handler.close()
                    actual_logger.removeHandler(handler)

            self._loggers.clear()

    def get_log_file(self, fork_id: int) -> Path:
        """
        Get the log file path for a specific fork.

        Args:
            fork_id: Fork identifier

        Returns:
            Path to the fork's log file
        """
        return self.log_dir / f"fork_{fork_id}_{self.session_timestamp}.log"


class ThreadSafeCounter:
    """
    Thread-safe counter for tracking events across forks.
    """

    def __init__(self, initial: int = 0):
        """
        Initialize counter.

        Args:
            initial: Initial counter value
        """
        self._value = initial
        self._lock = threading.Lock()

    def increment(self) -> int:
        """
        Increment counter and return new value.

        Returns:
            New counter value
        """
        with self._lock:
            self._value += 1
            return self._value

    def decrement(self) -> int:
        """
        Decrement counter and return new value.

        Returns:
            New counter value
        """
        with self._lock:
            self._value -= 1
            return self._value

    def get(self) -> int:
        """
        Get current counter value.

        Returns:
            Current counter value
        """
        with self._lock:
            return self._value

    def reset(self) -> None:
        """Reset counter to zero."""
        with self._lock:
            self._value = 0


def setup_logging(verbose: bool = False) -> None:
    """
    Setup global logging configuration.

    Args:
        verbose: Enable verbose (DEBUG level) logging
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=LOG_DATE_FORMAT,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)


class ProgressTracker:
    """
    Thread-safe progress tracker for monitoring fork execution.
    """

    def __init__(self, total_forks: int):
        """
        Initialize progress tracker.

        Args:
            total_forks: Total number of forks to track
        """
        self.total_forks = total_forks
        self._completed = ThreadSafeCounter(0)
        self._failed = ThreadSafeCounter(0)
        self._in_progress = ThreadSafeCounter(0)

    def start_fork(self) -> None:
        """Mark a fork as started."""
        self._in_progress.increment()

    def complete_fork(self, success: bool) -> None:
        """
        Mark a fork as completed.

        Args:
            success: Whether the fork completed successfully
        """
        self._in_progress.decrement()
        if success:
            self._completed.increment()
        else:
            self._failed.increment()

    def get_status(self) -> dict:
        """
        Get current progress status.

        Returns:
            Dictionary with completed, failed, in_progress counts
        """
        return {
            "total": self.total_forks,
            "completed": self._completed.get(),
            "failed": self._failed.get(),
            "in_progress": self._in_progress.get(),
            "pending": self.total_forks
            - self._completed.get()
            - self._failed.get()
            - self._in_progress.get(),
        }

    def is_complete(self) -> bool:
        """
        Check if all forks are complete.

        Returns:
            True if all forks are done (completed or failed)
        """
        status = self.get_status()
        return status["pending"] == 0 and status["in_progress"] == 0
