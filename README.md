# AIgent - Autonomous Browser Agent

An autonomous AI agent that controls a visible browser and solves arbitrary multi-step tasks without hardcoded scenarios or pre-written selectors.

## Features

- **Fully Autonomous**: Agent explores pages dynamically, finds elements through observation
- **No Hardcoded Selectors**: All selectors are generated dynamically from DOM analysis
- **Security Layer**: Asks for user confirmation before destructive actions (payments, form submissions, deletions)
- **Persistent Sessions**: Login once manually, agent continues in the same browser profile
- **Context Management**: Doesn't send entire HTML pages to LLM - uses summaries and targeted queries
- **Sub-agent Architecture**: DOM Analyst sub-agent for intelligent element selection
- **Error Recovery**: Automatic retries, scrolling, popup closing, alternative element selection
- **Full Logging**: JSON logs and screenshots for every step

## Installation

### Prerequisites

- Python 3.12+
- Playwright browsers

### Setup

```bash
# Clone and enter directory
cd AIgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Install Playwright browsers
playwright install chromium
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# LLM Provider (anthropic or openai)
LLM_PROVIDER=anthropic

# API Keys (set the one for your provider)
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Optional: Custom models
# ANTHROPIC_MODEL=claude-sonnet-4-20250514
# OPENAI_MODEL=gpt-4o

# Browser settings (defaults shown)
# USER_DATA_DIR=./profiles/default
# HEADLESS=false
# VIEWPORT_WIDTH=1280
# VIEWPORT_HEIGHT=900

# Agent settings (defaults shown)
# MAX_STEPS=50
# MAX_RETRIES=3
# QUERY_DOM_LIMIT=12
```

## Usage

### Start the Agent

```bash
python -m src.app.cli
```

The browser will open (non-headless by default). You'll see a prompt where you can enter tasks.

### Commands

| Command | Description |
|---------|-------------|
| `<task>` | Enter a natural language task for the agent |
| `go <url>` | Navigate to a URL manually |
| `url` | Show current page URL |
| `help` | Show help message |
| `quit` | Exit the agent |

### Example Tasks

```
# Search and navigation
Search for "python tutorials" on Google and click the first result

# E-commerce (stops before payment)
Open Яндекс Лавку, find hot dogs, add one to cart, but don't checkout

# Form filling
Find the contact form and fill in: name "John", email "john@test.com"

# Multi-step
Go to github.com, search for "playwright python", and star the first repository
```

## Persistent Sessions

The agent uses Playwright's persistent context. This means:

1. **First run**: Browser opens fresh
2. **Login manually**: You can login to any site in the browser window
3. **Sessions persist**: Close and restart the agent - you'll still be logged in

Sessions are stored in `./profiles/default/` by default. To use a different profile:

```bash
USER_DATA_DIR=./profiles/work python -m src.app.cli
```

## Security Layer

The agent will **stop and ask for confirmation** before:

- Confirming payments or orders
- Submitting forms that send messages
- Deleting content (emails, files, etc.)
- Any action on payment-related pages

Example prompt:
```
╭─────────────────────────────────────────╮
│ Security Check Required                  │
│                                          │
│ Action: Click on element containing 'pay'│
│ Risk: destructive                        │
│ Reason: Click on element containing 'pay'│
╰─────────────────────────────────────────╯

Confirm (yes/no):
```

## Logs and Screenshots

Each run creates a timestamped directory:

```
runs/
  20240115_143022/
    logs.jsonl        # All tool calls in JSON Lines format
    screenshots/
      step_0001.png   # Screenshot after each observation
      step_0002.png
      ...
```

### Log Format

```json
{"timestamp":"2024-01-15T14:30:22","tool":"query_dom","args":{"query":"login"},"result":"3 candidates found","success":true}
{"timestamp":"2024-01-15T14:30:23","tool":"click","args":{"selector":"button:has-text(\"Login\")"},"result":{"success":true},"success":true}
```

## Architecture

```
src/
  app/
    cli.py           # CLI entry point
    config.py        # Configuration from env
    logging.py       # JSON logging, console output
  agent/
    orchestrator.py  # Main plan/act/observe loop
    memory.py        # Context compression, history
    prompts.py       # System prompts
    policies.py      # Security classification
    errors.py        # Error recovery strategies
    subagents/
      dom_analyst.py # Element selection sub-agent
  browser/
    controller.py    # Playwright wrapper
    observation.py   # Page state observation
    selectors.py     # Dynamic selector generation
  tools/
    registry.py      # Tool registration for LLM
    actions.py       # Browser actions (click, type, etc.)
    dom.py           # query_dom implementation
    screenshots.py   # Screenshot tool
  llm/
    base.py          # Provider interface
    anthropic_provider.py
    openai_provider.py
```

## How It Works

### Context Management

Instead of sending entire HTML pages:

1. **observe()**: Returns URL + title + visible text summary + screenshot path
2. **query_dom(query)**: Returns top-N interactive elements matching query
3. **History compression**: Only recent steps in detail, older steps summarized

### Dynamic Selectors

The agent never uses hardcoded selectors. For each element found:

1. Try stable attributes: `data-testid`, `aria-label`, `name`
2. Try unique ID (if not auto-generated)
3. Build CSS path: `div.container > ul > li:nth-of-type(3) > a`
4. Fallback: Playwright text selector `:has-text("...")`

### Error Recovery

When actions fail, the agent tries:

1. Wait for element to appear
2. Scroll to find element
3. Close popups
4. Try alternative candidates from query_dom
5. Give up and report failure

## Debugging

### Increase Verbosity

The agent prints all tool calls to the terminal. For more detail:

```bash
# See raw LLM responses
export DEBUG=1
python -m src.app.cli
```

### Common Issues

**Browser doesn't start**
```bash
# Reinstall Playwright
playwright install chromium --with-deps
```

**Element not found**
- The page might need more time to load
- Try scrolling: agent should do this automatically
- Check screenshots in `runs/<timestamp>/screenshots/`

**API errors**
- Verify your API key is set correctly
- Check API quotas/limits

**Selectors failing**
- Dynamic sites may change DOM structure
- The agent will try alternative selectors
- Check `logs.jsonl` for what selectors were tried

### Reading Logs

```bash
# Pretty print logs
cat runs/*/logs.jsonl | python -m json.tool

# Filter by tool
grep '"tool":"click"' runs/*/logs.jsonl

# Find failures
grep '"success":false' runs/*/logs.jsonl
```

## Recording Demo Video

1. Start the agent: `python -m src.app.cli`
2. Start screen recording (OBS, QuickTime, etc.)
3. Enter task: `Открой google.com, найди поиск, введи "AI agent" и нажми поиск`
4. Watch the agent work
5. Stop recording

Tips for demo:
- Use a clean browser profile
- Start with simple tasks
- Show the security confirmation on a "dangerous" action
- Show the logs/screenshots after

## Extending

### Adding New Tools

```python
# In src/tools/actions.py
@registry.register(
    name="my_tool",
    description="What this tool does",
    parameters={
        "arg1": {"type": "string", "description": "..."},
    },
    required=["arg1"],
)
async def my_tool(arg1: str) -> dict:
    # Implementation
    return {"result": "..."}
```

### Custom LLM Provider

Implement `LLMProvider` interface in `src/llm/base.py` and add to `cli.py`.

## License

MIT
