"""CLI entry point for the browser agent."""

import asyncio
import sys

from src.agent.orchestrator import AgentStatus, Orchestrator
from src.app.config import config
from src.app.logging import (
    RunLogger,
    console,
    create_run_logger,
    get_user_input,
    print_welcome,
)
from src.browser.controller import BrowserController
from src.llm.base import LLMProvider
from src.tools.actions import register_action_tools
from src.tools.dom import register_dom_tools
from src.tools.registry import registry
from src.tools.screenshots import register_screenshot_tools


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider."""
    if config.LLM_PROVIDER == "anthropic":
        from src.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    else:
        from src.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()


async def run_agent_loop(
    browser: BrowserController,
    llm: LLMProvider,
    logger: RunLogger,
) -> None:
    """Main agent interaction loop."""
    # Register all tools
    register_action_tools(browser)
    register_dom_tools(browser)
    register_screenshot_tools(browser, logger.screenshots_dir)

    console.print(f"\n[dim]Registered tools: {', '.join(registry.list_tools())}[/dim]")
    console.print(f"[dim]Logs: {logger.log_file}[/dim]")
    console.print(f"[dim]Screenshots: {logger.screenshots_dir}[/dim]\n")

    orchestrator = Orchestrator(browser, llm, logger)

    while True:
        # Get task from user
        try:
            task = input("\n[Task] > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting...[/dim]")
            break

        if not task:
            continue

        if task.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if task.lower() == "help":
            print_help()
            continue

        if task.lower() == "url":
            url = await browser.get_url()
            console.print(f"[cyan]Current URL:[/cyan] {url}")
            continue

        if task.lower().startswith("go "):
            url = task[3:].strip()
            if not url.startswith("http"):
                url = "https://" + url
            await browser.navigate(url)
            console.print(f"[cyan]Navigated to:[/cyan] {url}")
            continue

        # Execute task
        console.print(f"\n[bold]Executing task:[/bold] {task}\n")

        try:
            result = await orchestrator.execute_task(task)

            # Log final report
            logger.log_final_report({
                "status": result.status.value,
                "summary": result.summary,
                "steps": result.steps_taken,
                "final_url": result.final_url,
            })

            # Handle different statuses
            if result.status == AgentStatus.NEED_USER_INPUT:
                console.print(f"\n[yellow]Agent needs input:[/yellow] {result.summary}")
                user_response = get_user_input("Your response:")
                if user_response:
                    # Continue with user input
                    new_task = f"{task}\n\nUser provided: {user_response}"
                    result = await orchestrator.execute_task(new_task)
                    logger.log_final_report({
                        "status": result.status.value,
                        "summary": result.summary,
                        "steps": result.steps_taken,
                        "final_url": result.final_url,
                    })

        except KeyboardInterrupt:
            console.print("\n[yellow]Task interrupted by user[/yellow]")
            orchestrator.stop()
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            logger.log_error(str(e))


def print_help() -> None:
    """Print help message."""
    console.print("""
[bold]Commands:[/bold]
  [cyan]<task>[/cyan]     Enter a task description for the agent to execute
  [cyan]go <url>[/cyan]  Navigate to a URL manually
  [cyan]url[/cyan]       Show current page URL
  [cyan]help[/cyan]      Show this help message
  [cyan]quit[/cyan]      Exit the agent

[bold]Example tasks:[/bold]
  - "Search for 'python tutorials' on Google"
  - "Find the login button and click it"
  - "Fill in the email field with test@example.com"
  - "Scroll down and find a product under $50"

[bold]Notes:[/bold]
  - The agent will ask for confirmation before destructive actions
  - Screenshots are saved in runs/<timestamp>/screenshots/
  - Logs are saved in runs/<timestamp>/logs.jsonl
""")


async def main_async() -> None:
    """Async main function."""
    # Check for API key
    try:
        config.get_api_key()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            f"[dim]Set {config.LLM_PROVIDER.upper()}_API_KEY environment variable[/dim]"
        )
        sys.exit(1)

    config.ensure_dirs()

    print_welcome()

    console.print(f"[dim]LLM Provider: {config.LLM_PROVIDER}[/dim]")
    console.print(f"[dim]Model: {config.get_model_name()}[/dim]")
    console.print(f"[dim]Profile: {config.USER_DATA_DIR}[/dim]")
    console.print(f"[dim]Headless: {config.HEADLESS}[/dim]")

    # Initialize components
    browser = BrowserController()
    llm = get_llm_provider()
    logger = create_run_logger()

    try:
        console.print("\n[dim]Starting browser...[/dim]")
        await browser.start()
        console.print("[green]Browser ready![/green]")

        # Navigate to a starting page
        await browser.navigate("about:blank")

        await run_agent_loop(browser, llm, logger)

    finally:
        console.print("\n[dim]Closing browser...[/dim]")
        await browser.stop()
        logger.close()
        console.print("[dim]Done.[/dim]")


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")


if __name__ == "__main__":
    main()
