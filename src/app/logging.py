"""Logging utilities for tool calls and agent actions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class RunLogger:
    """Logger for a single agent run."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.screenshots_dir = run_dir / "screenshots"
        self.log_file = run_dir / "logs.jsonl"
        self.step_count = 0

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
        """Log a tool call with clean formatting."""
        self.step_count += 1

        # Create result summary
        result_summary = self._summarize_result(result)

        # Write to file (detailed)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": self.step_count,
            "tool": tool,
            "args": args,
            "result": result if isinstance(result, (dict, list, str, int, float, bool)) else str(result),
            "success": success,
        }
        json_line = json.dumps(entry, ensure_ascii=False)
        self._log_handle.write(json_line + "\n")
        self._log_handle.flush()

        # Print to console (clean format)
        self._print_tool_call(tool, args, result_summary, success)

    def log_agent_thought(self, thought: str) -> None:
        """Log agent reasoning/thinking."""
        # Clean up the thought
        thought = thought.strip()
        if not thought:
            return

        # Truncate long thoughts
        if len(thought) > 300:
            thought = thought[:297] + "..."

        console.print(f"\n[bold cyan]🤖 Agent:[/bold cyan] {thought}")

    def log_subagent(self, name: str, message: str) -> None:
        """Log sub-agent activity."""
        console.print(f"  [dim magenta]↳ {name}:[/dim magenta] {message}")

    def log_security_check(self, action: str, reason: str) -> None:
        """Log security check requiring user confirmation."""
        console.print()
        console.print(
            Panel(
                f"[bold yellow]⚠️  Security Check Required[/bold yellow]\n\n"
                f"[bold]Action:[/bold] {action}\n"
                f"[bold]Reason:[/bold] {reason}",
                border_style="yellow",
                title="[bold]Confirmation Needed[/bold]",
            )
        )

    def log_error(self, error: str) -> None:
        """Log an error."""
        console.print(f"\n[bold red]❌ Error:[/bold red] {error}")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "message": error,
        }
        self._log_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._log_handle.flush()

    def log_final_report(self, report: dict[str, Any]) -> None:
        """Log the final execution report."""
        status = report.get("status", "unknown")
        steps = report.get("steps", 0)
        summary = report.get("summary", "N/A")

        # Choose style based on status
        if status == "done":
            icon = "✅"
            title = "Task Completed"
            border_style = "green"
        elif status == "failed":
            icon = "❌"
            title = "Task Failed"
            border_style = "red"
        elif status == "need_user_input":
            icon = "⏸️"
            title = "Waiting for User"
            border_style = "yellow"
        else:
            icon = "ℹ️"
            title = "Execution Finished"
            border_style = "blue"

        console.print()
        console.print(
            Panel(
                f"[bold]{icon} {title}[/bold]\n\n"
                f"[bold]Status:[/bold] {status}\n"
                f"[bold]Steps:[/bold] {steps}\n\n"
                f"[bold]Summary:[/bold]\n{summary}",
                border_style=border_style,
                title=f"[bold]{title}[/bold]",
            )
        )

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "final_report",
            "report": report,
        }
        self._log_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._log_handle.flush()

    def _summarize_result(self, result: Any, max_len: int = 100) -> str:
        """Create a compact summary of a result."""
        if result is None:
            return "null"
        if isinstance(result, bool):
            return "✓" if result else "✗"
        if isinstance(result, (int, float)):
            return str(result)
        if isinstance(result, str):
            if len(result) > max_len:
                return result[:max_len] + "..."
            return result
        if isinstance(result, dict):
            # Handle common result patterns
            if "success" in result:
                if result.get("success"):
                    if "url" in result:
                        return f"✓ → {result['url']}"
                    if "typed" in result:
                        return f"✓ typed '{result['typed']}'"
                    if "clicked" in result:
                        return f"✓ clicked"
                    if "pressed" in result:
                        return f"✓ pressed {result['pressed']}"
                    if "scrolled" in result:
                        return f"✓ {result['scrolled']}"
                    return "✓"
                else:
                    return f"✗ {result.get('error', 'failed')[:50]}"

            if "error" in result:
                error = result["error"]
                if "Timeout" in error:
                    return "✗ timeout"
                return f"✗ {error[:50]}"

            if "candidates" in result:
                count = len(result["candidates"])
                if count > 0:
                    first = result["candidates"][0]
                    text = first.get("text", "")[:30] or first.get("selector", "")[:30]
                    return f"found {count} elements ('{text}'...)"
                return "no elements found"

            if "elements" in result:
                return f"found {len(result['elements'])} elements"

            return json.dumps(result, ensure_ascii=False)[:max_len]
        if isinstance(result, list):
            return f"[{len(result)} items]"
        return str(result)[:max_len]

    def _print_tool_call(self, tool: str, args: dict[str, Any], result: str, success: bool) -> None:
        """Print tool call in clean format."""
        # Format args nicely
        args_parts = []
        for key, value in args.items():
            if isinstance(value, str):
                # Truncate long strings
                if len(value) > 40:
                    value = value[:37] + "..."
                args_parts.append(f'{key}="{value}"')
            else:
                args_parts.append(f"{key}={value}")
        args_str = ", ".join(args_parts)

        # Choose icon based on tool type
        tool_icons = {
            "navigate_to_url": "🌐",
            "click": "👆",
            "type_text": "⌨️",
            "press": "⏎",
            "scroll": "📜",
            "query_dom": "🔍",
            "get_all_elements": "📋",
            "wait": "⏳",
            "hover": "👆",
            "back": "⬅️",
            "take_screenshot": "📸",
            "close_popups": "❌",
            "get_current_url": "🔗",
        }
        icon = tool_icons.get(tool, "🔧")

        # Status indicator
        status = "[green]✓[/green]" if success else "[red]✗[/red]"

        # Print formatted line
        console.print(f"  {icon} [blue]{tool}[/blue]({args_str}) {status} {result}")


def create_run_logger() -> RunLogger:
    """Create a new run logger with timestamped directory."""
    from src.app.config import config

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = config.OUTPUT_RUNS_DIR / timestamp
    return RunLogger(run_dir)


def print_welcome() -> None:
    """Print welcome message."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]🤖 AIgent - Autonomous Browser Agent[/bold cyan]\n\n"
            "Type your task and press Enter. Type 'quit' to exit.\n"
            "The agent will ask for confirmation before sensitive actions.",
            border_style="cyan",
            title="[bold]Welcome[/bold]",
        )
    )
    console.print()


def print_task_start(task: str) -> None:
    """Print task start message."""
    console.print(
        Panel(
            f"[bold]{task}[/bold]",
            border_style="blue",
            title="[bold]📋 New Task[/bold]",
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
