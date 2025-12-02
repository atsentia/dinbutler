"""Output formatting utilities for DinButler CLI.

Provides consistent JSON and text output formatting.
"""

import json
import sys
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


console = Console() if RICH_AVAILABLE else None


def output_json(data: Any, pretty: bool = True) -> None:
    """Output data as JSON."""
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))


def output_text(message: str) -> None:
    """Output plain text message."""
    print(message)


def output_error(message: str, exit_code: int = 1) -> None:
    """Output error message and optionally exit."""
    if RICH_AVAILABLE and console:
        console.print(f"[red]Error:[/red] {message}", style="bold")
    else:
        print(f"Error: {message}", file=sys.stderr)
    if exit_code:
        sys.exit(exit_code)


def output_success(message: str) -> None:
    """Output success message."""
    if RICH_AVAILABLE and console:
        console.print(f"[green]✓[/green] {message}")
    else:
        print(f"✓ {message}")


def output_table(
    headers: List[str],
    rows: List[List[str]],
    title: Optional[str] = None
) -> None:
    """Output data as a formatted table."""
    if RICH_AVAILABLE and console:
        table = Table(title=title)
        for header in headers:
            table.add_column(header)
        for row in rows:
            table.add_row(*row)
        console.print(table)
    else:
        # Simple text table fallback
        if title:
            print(f"\n{title}")
            print("-" * len(title))

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        # Print header
        header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        print(header_line)
        print("-" * len(header_line))

        # Print rows
        for row in rows:
            row_line = "  ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(row))
            print(row_line)


def format_sandbox_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """Format sandbox info for output."""
    return {
        "sandbox_id": info.get("sandbox_id", ""),
        "template": info.get("template_id", info.get("template", "")),
        "state": info.get("state", ""),
        "started_at": str(info.get("started_at", "")),
    }


def format_file_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Format file entry for output."""
    return {
        "name": entry.get("name", ""),
        "type": entry.get("type", ""),
        "size": entry.get("size", 0),
        "path": entry.get("path", ""),
    }
