"""Logging utilities for tool calls and agent actions with i18n support."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.app.i18n import t, set_language

console = Console()


class RunLogger:
    """Logger for a single agent run with Russian language support."""

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

        # Initialize language from config
        from src.app.config import config
        set_language(config.LANGUAGE)

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

        console.print(f"\n[bold cyan]{t('agent_says')}:[/bold cyan] {thought}")

    def log_orchestrator(self, message: str) -> None:
        """Log orchestrator communication."""
        console.print(f"[bold blue]{t('orchestrator_says')}:[/bold blue] {message}")

    def log_subagent(self, name: str, message: str) -> None:
        """Log sub-agent activity with Russian labels."""
        # Translate common subagent names
        translated_name = name
        if name.lower() == "dom":
            translated_name = t("dom_analyst")

        console.print(f"  [dim magenta]{t('subagent_says', name=translated_name)}:[/dim magenta] {message}")

    def log_llm_communication(self, direction: str, content: str) -> None:
        """Log LLM communication (request/response)."""
        if len(content) > 200:
            content = content[:197] + "..."
        console.print(f"  [dim yellow]{t('llm_says')} ({direction}):[/dim yellow] {content}")

    def log_security_check(self, action: str, reason: str) -> None:
        """Log security check requiring user confirmation."""
        console.print()
        console.print(
            Panel(
                f"[bold yellow]{t('security_check_required')}[/bold yellow]\n\n"
                f"[bold]{t('security_action')}:[/bold] {action}\n"
                f"[bold]{t('security_reason')}:[/bold] {reason}",
                border_style="yellow",
                title=f"[bold]{t('security_confirm_needed')}[/bold]",
            )
        )

    def log_error(self, error: str) -> None:
        """Log an error."""
        console.print(f"\n[bold red]❌ {t('error')}:[/bold red] {error}")
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

        # Choose style based on status with Russian labels
        if status == "done":
            icon = "✅"
            title = t("report_task_completed")
            border_style = "green"
        elif status == "failed":
            icon = "❌"
            title = t("report_task_failed")
            border_style = "red"
        elif status == "need_user_input":
            icon = "⏸️"
            title = t("report_waiting_user")
            border_style = "yellow"
        else:
            icon = "ℹ️"
            title = t("report_execution_finished")
            border_style = "blue"

        console.print()
        console.print(
            Panel(
                f"[bold]{icon} {title}[/bold]\n\n"
                f"[bold]{t('report_status')}:[/bold] {status}\n"
                f"[bold]{t('report_steps')}:[/bold] {steps}\n\n"
                f"[bold]{t('report_summary')}:[/bold]\n{summary}",
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
        """Create a compact summary of a result in Russian."""
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
            # Handle common result patterns with Russian
            if "success" in result:
                if result.get("success"):
                    if "url" in result:
                        return f"✓ → {result['url']}"
                    if "typed" in result:
                        return t("result_typed", text=result["typed"])
                    if "clicked" in result:
                        return f"✓ {t('result_clicked')}"
                    if "pressed" in result:
                        return t("result_pressed", keys=result["pressed"])
                    if "scrolled" in result:
                        return t("result_scrolled", direction=result["scrolled"])
                    return f"✓ {t('result_success')}"
                else:
                    return f"✗ {result.get('error', t('result_failed'))[:50]}"

            if "error" in result:
                error = result["error"]
                if "Timeout" in error:
                    return f"✗ {t('result_timeout')}"
                return f"✗ {error[:50]}"

            if "candidates" in result:
                count = len(result["candidates"])
                if count > 0:
                    first = result["candidates"][0]
                    text = first.get("text", "")[:30] or first.get("selector", "")[:30]
                    return f"{t('result_found_elements', count=count)} ('{text}'...)"
                return t("result_no_elements")

            if "elements" in result:
                return t("result_found_elements", count=len(result["elements"]))

            return json.dumps(result, ensure_ascii=False)[:max_len]
        if isinstance(result, list):
            return f"[{len(result)} элементов]"
        return str(result)[:max_len]

    def _print_tool_call(self, tool: str, args: dict[str, Any], result: str, success: bool) -> None:
        """Print tool call in clean format with Russian descriptions."""
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

        # Choose icon and Russian description based on tool type
        tool_info = {
            "navigate_to_url": ("🌐", "tool_navigating"),
            "click": ("👆", "tool_clicking"),
            "type_text": ("⌨️", "tool_typing"),
            "press": ("⏎", "tool_pressing"),
            "scroll": ("📜", "tool_scrolling"),
            "query_dom": ("🔍", "tool_searching_dom"),
            "get_all_elements": ("📋", None),
            "wait": ("⏳", "tool_waiting"),
            "hover": ("👆", "tool_hovering"),
            "back": ("⬅️", "tool_going_back"),
            "take_screenshot": ("📸", "tool_screenshot"),
            "close_popups": ("❌", "tool_closing_popups"),
            "get_current_url": ("🔗", "tool_getting_url"),
        }
        icon, desc_key = tool_info.get(tool, ("🔧", None))

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
    """Print welcome message in Russian."""
    console.print()
    console.print(
        Panel(
            f"[bold cyan]{t('welcome_text')}[/bold cyan]",
            border_style="cyan",
            title=f"[bold]{t('welcome_title')}[/bold]",
        )
    )
    console.print()


def print_task_start(task: str) -> None:
    """Print task start message."""
    console.print(
        Panel(
            f"[bold]{task}[/bold]",
            border_style="blue",
            title=f"[bold]{t('new_task')}[/bold]",
        )
    )


def get_user_confirmation(prompt: str) -> bool:
    """Get yes/no confirmation from user in Russian."""
    console.print(f"\n[bold yellow]{prompt}[/bold yellow]")
    while True:
        response = input(t("confirm_yes_no")).strip().lower()
        if response in ("yes", "y", "да", "д"):
            return True
        if response in ("no", "n", "нет", "н"):
            return False
        console.print(f"[dim]{t('confirm_enter_yes_no')}[/dim]")


def get_user_input(prompt: str) -> str:
    """Get text input from user."""
    console.print(f"\n[bold cyan]{prompt}[/bold cyan]")
    return input("> ").strip()
