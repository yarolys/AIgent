"""Logging utilities for tool calls and agent actions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

console = Console()


class RunLogger:
    """Logger for a single agent run."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.screenshots_dir = run_dir / "screenshots"
        self.log_file = run_dir / "logs.jsonl"

        # Create directories
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Open log file
        self._log_handle = open(self.log_file, "a", encoding="utf-8")

    def close(self) -> None:
        """Close the log file."""
        self._log_handle.close()

    def log_tool_call(
        self,
        tool: str,
        args: dict[str, Any],
        result: Any,
        success: bool = True,
    ) -> None:
        """Log a tool call in JSONL format."""
        # Create compact result summary
        result_summary = self._summarize_result(result)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "args": args,
            "result": result_summary,
            "success": success,
        }

        # Write to file
        json_line = json.dumps(entry, ensure_ascii=False)
        self._log_handle.write(json_line + "\n")
        self._log_handle.flush()

        # Print to console
        self._print_tool_call(entry)

    def log_agent_thought(self, thought: str) -> None:
        """Log agent reasoning."""
        console.print(f"[dim cyan]Agent:[/dim cyan] {thought}")

    def log_subagent(self, name: str, message: str) -> None:
        """Log sub-agent activity."""
        console.print(f"[dim magenta]{name} Sub-agent:[/dim magenta] {message}")

    def log_security_check(self, action: str, reason: str) -> None:
        """Log security check."""
        console.print(
            Panel(
                f"[bold red]Security Check Required[/bold red]\n\n"
                f"Action: {action}\n"
                f"Reason: {reason}",
                border_style="red",
            )
        )

    def log_error(self, error: str) -> None:
        """Log an error."""
        console.print(f"[bold red]Error:[/bold red] {error}")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "message": error,
        }
        self._log_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._log_handle.flush()

    def log_final_report(self, report: dict[str, Any]) -> None:
        """Log the final execution report."""
        console.print("\n")
        console.print(
            Panel(
                f"[bold green]Execution Complete[/bold green]\n\n"
                f"Status: {report.get('status', 'unknown')}\n"
                f"Steps: {report.get('steps', 0)}\n"
                f"Summary: {report.get('summary', 'N/A')}",
                border_style="green",
            )
        )

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "final_report",
            "report": report,
        }
        self._log_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._log_handle.flush()

    def _summarize_result(self, result: Any, max_len: int = 200) -> str:
        """Create a compact summary of a result."""
        import os
        debug = os.environ.get("DEBUG_SELECTORS", "0") == "1"

        if result is None:
            return "null"
        if isinstance(result, bool):
            return str(result).lower()
        if isinstance(result, (int, float)):
            return str(result)
        if isinstance(result, str):
            if len(result) > max_len:
                return result[:max_len] + "..."
            return result
        if isinstance(result, dict):
            # For candidates, show count AND first selector for debugging
            if "candidates" in result:
                count = len(result['candidates'])
                if count > 0 and result['candidates']:
                    first_candidate = result['candidates'][0]
                    if debug:
                        print(f"  [DEBUG LOG] first_candidate keys: {list(first_candidate.keys())}")
                        print(f"  [DEBUG LOG] first_candidate: {first_candidate}")
                    first_selector = first_candidate.get('selector', 'NO_SELECTOR')
                    first_text = first_candidate.get('text', '')[:30]
                    if debug:
                        print(f"  [DEBUG LOG] first_selector = {repr(first_selector)}")
                        print(f"  [DEBUG LOG] first_text = {repr(first_text)}")
                    summary = f"{count} candidates (first: selector='{first_selector}', text='{first_text}')"
                    if debug:
                        print(f"  [DEBUG LOG] returning: {repr(summary)}")
                    return summary
                return f"{count} candidates found"
            if "path" in result:
                return f"path: {result['path']}"
            return json.dumps(result, ensure_ascii=False)[:max_len]
        if isinstance(result, list):
            return f"[{len(result)} items]"
        return str(result)[:max_len]

    def _print_tool_call(self, entry: dict[str, Any]) -> None:
        """Print tool call to console."""
        status = "[green]OK[/green]" if entry.get("success", True) else "[red]FAIL[/red]"

        # Format args compactly
        args_str = json.dumps(entry["args"], ensure_ascii=False)
        if len(args_str) > 80:
            args_str = args_str[:77] + "..."

        console.print(
            f"[blue]{entry['tool']}[/blue]({args_str}) -> {entry['result']} {status}"
        )


def create_run_logger() -> RunLogger:
    """Create a new run logger with timestamped directory."""
    from src.app.config import config

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = config.OUTPUT_RUNS_DIR / timestamp
    return RunLogger(run_dir)


def print_welcome() -> None:
    """Print welcome message."""
    console.print(
        Panel(
            "[bold]AIgent - Autonomous Browser Agent[/bold]\n"
            "Type your task and press Enter. Type 'quit' to exit.\n"
            "The agent will ask for confirmation before destructive actions.",
            border_style="blue",
        )
    )


def get_user_confirmation(prompt: str) -> bool:
    """Get yes/no confirmation from user."""
    console.print(f"\n[bold yellow]{prompt}[/bold yellow]")
    while True:
        response = input("Confirm (yes/no): ").strip().lower()
        if response in ("yes", "y"):
            return True
        if response in ("no", "n"):
            return False
        console.print("[dim]Please enter 'yes' or 'no'[/dim]")


def get_user_input(prompt: str) -> str:
    """Get text input from user."""
    console.print(f"\n[bold cyan]{prompt}[/bold cyan]")
    return input("> ").strip()
