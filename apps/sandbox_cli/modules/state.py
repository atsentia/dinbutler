"""State management for DinButler CLI.

Manages local state in .dinbutler/ directory for tracking current sandbox.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


DINBUTLER_DIR = ".dinbutler"
SANDBOX_ID_FILE = "sandbox_id"
CONFIG_FILE = "config.json"


def get_state_dir() -> Path:
    """Get or create .dinbutler directory in current working directory."""
    state_dir = Path.cwd() / DINBUTLER_DIR
    state_dir.mkdir(exist_ok=True)
    return state_dir


def save_sandbox_id(sandbox_id: str) -> None:
    """Save current sandbox ID to state file."""
    state_dir = get_state_dir()
    sandbox_file = state_dir / SANDBOX_ID_FILE
    sandbox_file.write_text(sandbox_id)


def get_sandbox_id() -> Optional[str]:
    """Get saved sandbox ID from state file."""
    state_dir = Path.cwd() / DINBUTLER_DIR
    sandbox_file = state_dir / SANDBOX_ID_FILE

    if sandbox_file.exists():
        sandbox_id = sandbox_file.read_text().strip()
        if sandbox_id:
            return sandbox_id
    return None


def clear_state() -> None:
    """Clear all state files."""
    state_dir = Path.cwd() / DINBUTLER_DIR
    if state_dir.exists():
        sandbox_file = state_dir / SANDBOX_ID_FILE
        if sandbox_file.exists():
            sandbox_file.unlink()
        config_file = state_dir / CONFIG_FILE
        if config_file.exists():
            config_file.unlink()


def get_config() -> Dict[str, Any]:
    """Get local configuration."""
    state_dir = Path.cwd() / DINBUTLER_DIR
    config_file = state_dir / CONFIG_FILE

    if config_file.exists():
        return json.loads(config_file.read_text())
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save local configuration."""
    state_dir = get_state_dir()
    config_file = state_dir / CONFIG_FILE
    config_file.write_text(json.dumps(config, indent=2))


def get_sandbox_id_or_arg(sandbox_id: Optional[str]) -> Optional[str]:
    """Get sandbox ID from argument or saved state."""
    if sandbox_id:
        return sandbox_id
    return get_sandbox_id()
