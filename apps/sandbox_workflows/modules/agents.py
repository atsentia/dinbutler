"""
SandboxForkAgent - Claude agent for parallel sandbox experiments.

Implements a Claude-powered agent that operates within sandbox environments,
respecting security hooks and logging all interactions.
"""

import asyncio
import json
import logging
import subprocess
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from anthropic import Anthropic

from apps.sandbox_workflows.modules.hooks import HookManager, SecurityViolation, HookContext
from apps.sandbox_workflows.modules.logs import ForkLogger
from apps.sandbox_workflows.modules.constants import (
    MAX_AGENT_TURNS,
    DEFAULT_MODEL,
    MODEL_IDENTIFIERS,
    ALLOWED_PATHS,
    MAX_TOOL_CALLS_PER_TURN,
    AGENT_MAX_RETRIES,
    AGENT_RETRY_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


class SandboxForkAgent:
    """
    Claude agent configured for sandbox work.

    Executes tasks within a sandbox environment using Claude's API with tool use.
    All tool calls are validated by security hooks and logged for audit purposes.
    """

    def __init__(
        self,
        fork_num: int,
        sandbox_id: str,
        repo_url: Optional[str] = None,
        branch: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        system_prompt: Optional[str] = None,
        hooks: Optional[HookManager] = None,
        logger_instance: Optional[ForkLogger] = None,
        sandbox_root: Optional[Path] = None,
    ):
        """
        Initialize the sandbox agent.

        Args:
            fork_num: Fork number (for logging and identification)
            sandbox_id: Unique sandbox identifier
            repo_url: Git repository URL (if applicable)
            branch: Git branch name (if applicable)
            model: Claude model to use (short name or full identifier)
            system_prompt: Custom system prompt (overrides default)
            hooks: Hook manager for security validation
            logger_instance: Fork logger for structured logging
            sandbox_root: Root directory of the sandbox
        """
        self.fork_num = fork_num
        self.sandbox_id = sandbox_id
        self.repo_url = repo_url
        self.branch = branch
        self.model = self._resolve_model_name(model)
        self.logger_instance = logger_instance
        self.sandbox_root = sandbox_root or Path.cwd()

        # Initialize hooks with sandbox root
        self.hooks = hooks or HookManager(self.sandbox_root)

        # Initialize Anthropic client
        self.client = Anthropic()

        # Load system prompt
        self.system_prompt = system_prompt or self._load_default_system_prompt()

        # Metrics tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        self.turns = 0
        self.tool_calls = 0
        self.errors = 0

    def _resolve_model_name(self, model: str) -> str:
        """
        Resolve short model names to full identifiers.

        Args:
            model: Short model name (e.g., "sonnet") or full identifier

        Returns:
            Full model identifier
        """
        if model in MODEL_IDENTIFIERS:
            return MODEL_IDENTIFIERS[model]
        return model

    def _load_default_system_prompt(self) -> str:
        """
        Load the default system prompt from template.

        Returns:
            Formatted system prompt
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / "system_prompt.md"

        if not prompt_path.exists():
            logger.warning(f"System prompt template not found at {prompt_path}, using minimal prompt")
            return "You are a coding assistant working in an isolated sandbox."

        try:
            template = prompt_path.read_text()

            # Replace placeholders (note: the template uses {task_prompt} which we'll handle in run())
            return template.format(
                sandbox_id=self.sandbox_id,
                fork_num=self.fork_num,
                repo_url=self.repo_url or "local",
                branch=self.branch or "main",
            )
        except Exception as e:
            logger.error(f"Failed to load system prompt template: {e}")
            return "You are a coding assistant working in an isolated sandbox."

    async def run(
        self,
        task_prompt: str,
        max_turns: int = MAX_AGENT_TURNS,
    ) -> Dict[str, Any]:
        """
        Execute agent with task prompt, handling tool use loop.

        Args:
            task_prompt: Task description for the agent
            max_turns: Maximum number of agent turns

        Returns:
            Dictionary with execution results:
            - success: Whether task completed successfully
            - final_response: Agent's final response
            - turns: Number of turns taken
            - tool_calls: Total tool calls made
            - errors: Number of errors encountered
            - total_tokens: Total tokens used
            - total_cost: Estimated cost in USD
        """
        self._log("Starting agent execution", "info")
        self._log(f"Task: {task_prompt[:200]}...", "debug")

        # Insert task prompt into system prompt
        system_prompt = self.system_prompt.replace("{task_prompt}", task_prompt)

        # Initialize conversation
        messages = [
            {
                "role": "user",
                "content": task_prompt,
            }
        ]

        final_response = None

        try:
            for turn in range(max_turns):
                self.turns = turn + 1
                self._log(f"Turn {self.turns}/{max_turns}", "info")

                # Call Claude API
                response = await self._call_claude(system_prompt, messages)

                # Update metrics
                if hasattr(response, "usage"):
                    self.total_tokens += response.usage.input_tokens + response.usage.output_tokens
                    self.total_cost = self._calculate_cost(self.total_tokens, self.model)

                # Handle response
                if response.stop_reason == "end_turn":
                    # Agent finished without tool use
                    final_response = self._extract_text_content(response)
                    self._log("Agent completed task (end_turn)", "info")
                    break

                elif response.stop_reason == "tool_use":
                    # Agent wants to use tools
                    tool_results = await self._process_tool_calls(response.content)

                    # Add assistant's response to messages
                    messages.append({
                        "role": "assistant",
                        "content": response.content,
                    })

                    # Add tool results to messages
                    messages.append({
                        "role": "user",
                        "content": tool_results,
                    })

                    # Continue loop to get next response

                elif response.stop_reason == "max_tokens":
                    self._log("Response truncated due to max_tokens", "warning")
                    final_response = self._extract_text_content(response)
                    break

                else:
                    self._log(f"Unexpected stop_reason: {response.stop_reason}", "warning")
                    final_response = self._extract_text_content(response)
                    break

            else:
                # Reached max_turns
                self._log(f"Reached max_turns limit ({max_turns})", "warning")
                final_response = "Task incomplete: reached maximum turn limit"

        except Exception as e:
            self._log(f"Agent execution failed: {e}", "error")
            self.errors += 1
            final_response = f"Error: {str(e)}"

        # Return results
        return {
            "success": self.errors == 0 and final_response is not None,
            "final_response": final_response or "",
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "errors": self.errors,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }

    async def _call_claude(
        self,
        system_prompt: str,
        messages: List[Dict],
    ) -> Any:
        """
        Call Claude API with current conversation state.

        Args:
            system_prompt: System prompt for the agent
            messages: Conversation history

        Returns:
            API response object
        """
        # Define available tools (based on Claude Code standard tools)
        tools = [
            {
                "name": "Bash",
                "description": "Execute a bash command in the sandbox",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "Read",
                "description": "Read a file from the sandbox filesystem",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the file to read",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "Write",
                "description": "Write content to a file in the sandbox",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the file to write",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
            {
                "name": "Edit",
                "description": "Edit a file by replacing old_string with new_string",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the file to edit",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "The exact string to replace",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "The replacement string",
                        },
                    },
                    "required": ["file_path", "old_string", "new_string"],
                },
            },
            {
                "name": "Glob",
                "description": "Find files matching a glob pattern",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g., '**/*.py')",
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory to search in (optional)",
                        },
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "Grep",
                "description": "Search for a pattern in files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regular expression pattern to search for",
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to search in (optional)",
                        },
                        "glob": {
                            "type": "string",
                            "description": "Glob pattern to filter files (optional)",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        ]

        # Call API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        return response

    async def _process_tool_calls(
        self,
        content: List[Dict],
    ) -> List[Dict]:
        """
        Process tool calls from Claude's response.

        Args:
            content: Response content blocks (text + tool_use)

        Returns:
            List of tool result content blocks
        """
        tool_results = []

        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                self._log(f"Tool call: {tool_name}", "info")
                self._log(f"Parameters: {tool_input}", "debug")

                # Execute tool with security hooks
                try:
                    result = self._execute_tool(tool_name, tool_input)
                    self.tool_calls += 1

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": str(result),
                    })

                except SecurityViolation as e:
                    self._log(f"Security violation: {e}", "error")
                    self.errors += 1

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"SECURITY VIOLATION: {str(e)}",
                        "is_error": True,
                    })

                except Exception as e:
                    self._log(f"Tool execution failed: {e}", "error")
                    self.errors += 1

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"ERROR: {str(e)}",
                        "is_error": True,
                    })

        return tool_results

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool call with security validation.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool parameters

        Returns:
            Tool execution result as string

        Raises:
            SecurityViolation: If tool call violates security policies
            Exception: If tool execution fails
        """
        # Use hook context for pre/post validation
        with HookContext(self.hooks, tool_name, tool_input) as ctx:
            # Route to appropriate tool implementation
            if tool_name == "Bash":
                result = self._tool_bash(tool_input)
            elif tool_name == "Read":
                result = self._tool_read(tool_input)
            elif tool_name == "Write":
                result = self._tool_write(tool_input)
            elif tool_name == "Edit":
                result = self._tool_edit(tool_input)
            elif tool_name == "Glob":
                result = self._tool_glob(tool_input)
            elif tool_name == "Grep":
                result = self._tool_grep(tool_input)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            ctx.set_result(result)
            return result

    def _tool_bash(self, params: Dict[str, Any]) -> str:
        """Execute bash command via sandbox CLI."""
        command = params["command"]

        # Execute via subprocess (sandbox CLI would be used in production)
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.sandbox_root),
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            if result.returncode != 0:
                output += f"\nExit code: {result.returncode}"

            return output or "Command executed successfully (no output)"

        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 120 seconds"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_read(self, params: Dict[str, Any]) -> str:
        """Read file contents."""
        file_path = Path(params["file_path"])

        # Make path relative to sandbox root if needed
        if not file_path.is_absolute():
            file_path = self.sandbox_root / file_path

        try:
            content = file_path.read_text()
            return content
        except FileNotFoundError:
            return f"ERROR: File not found: {file_path}"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_write(self, params: Dict[str, Any]) -> str:
        """Write content to file."""
        file_path = Path(params["file_path"])
        content = params["content"]

        # Make path relative to sandbox root if needed
        if not file_path.is_absolute():
            file_path = self.sandbox_root / file_path

        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content)
            return f"Successfully wrote {len(content)} bytes to {file_path}"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_edit(self, params: Dict[str, Any]) -> str:
        """Edit file by replacing text."""
        file_path = Path(params["file_path"])
        old_string = params["old_string"]
        new_string = params["new_string"]

        # Make path relative to sandbox root if needed
        if not file_path.is_absolute():
            file_path = self.sandbox_root / file_path

        try:
            content = file_path.read_text()

            if old_string not in content:
                return f"ERROR: old_string not found in {file_path}"

            # Count occurrences
            count = content.count(old_string)
            if count > 1:
                return f"ERROR: old_string appears {count} times in {file_path}, not unique"

            # Replace
            new_content = content.replace(old_string, new_string, 1)
            file_path.write_text(new_content)

            return f"Successfully replaced 1 occurrence in {file_path}"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_glob(self, params: Dict[str, Any]) -> str:
        """Find files matching glob pattern."""
        pattern = params["pattern"]
        search_path = params.get("path")

        if search_path:
            base_path = Path(search_path)
            if not base_path.is_absolute():
                base_path = self.sandbox_root / base_path
        else:
            base_path = self.sandbox_root

        try:
            matches = list(base_path.glob(pattern))
            if not matches:
                return f"No files found matching pattern: {pattern}"

            # Return relative paths
            result_lines = []
            for match in sorted(matches):
                try:
                    rel_path = match.relative_to(self.sandbox_root)
                    result_lines.append(str(rel_path))
                except ValueError:
                    result_lines.append(str(match))

            return "\n".join(result_lines)
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _tool_grep(self, params: Dict[str, Any]) -> str:
        """Search for pattern in files."""
        pattern = params["pattern"]
        search_path = params.get("path")
        glob_pattern = params.get("glob", "**/*")

        if search_path:
            base_path = Path(search_path)
            if not base_path.is_absolute():
                base_path = self.sandbox_root / base_path
        else:
            base_path = self.sandbox_root

        try:
            import re
            regex = re.compile(pattern)

            matches = []
            for file_path in base_path.glob(glob_pattern):
                if not file_path.is_file():
                    continue

                try:
                    content = file_path.read_text()
                    for line_num, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(self.sandbox_root)
                            matches.append(f"{rel_path}:{line_num}:{line}")
                except Exception:
                    # Skip files that can't be read
                    continue

            if not matches:
                return f"No matches found for pattern: {pattern}"

            return "\n".join(matches[:100])  # Limit to 100 matches
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _extract_text_content(self, response: Any) -> str:
        """Extract text content from API response."""
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """
        Estimate cost based on token usage.

        Args:
            tokens: Total tokens used
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        # Approximate pricing (as of 2025)
        pricing = {
            "claude-sonnet-4-5-20250929": 3.0 / 1_000_000,  # $3 per MTok
            "claude-opus-4-20250514": 15.0 / 1_000_000,     # $15 per MTok
            "claude-3-5-haiku-20241022": 1.0 / 1_000_000,   # $1 per MTok
        }

        rate = pricing.get(model, 3.0 / 1_000_000)
        return tokens * rate

    def _log(self, message: str, level: str = "info") -> None:
        """
        Log a message using the fork logger.

        Args:
            message: Log message
            level: Log level (debug, info, warning, error, critical)
        """
        if self.logger_instance:
            self.logger_instance.log(self.fork_num, message, level)
        else:
            # Fallback to module logger
            log_func = getattr(logger, level, logger.info)
            log_func(f"Fork {self.fork_num}: {message}")
