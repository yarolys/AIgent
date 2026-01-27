"""Text processing utilities."""

import re


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace."""
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_visible_text(html_text: str, max_length: int = 2000) -> str:
    """Extract and clean visible text from raw text content."""
    # Remove script/style content patterns
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Clean and truncate
    text = clean_text(text)
    return truncate_text(text, max_length)


def summarize_text(text: str, max_sentences: int = 3) -> str:
    """Create a brief summary of text (first N sentences)."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return ". ".join(sentences[:max_sentences]) + "." if sentences else ""


def normalize_selector_text(text: str) -> str:
    """Normalize text for selector matching."""
    return clean_text(text.lower())


def score_text_match(query: str, target: str) -> float:
    """Score how well a query matches target text (0.0 to 1.0)."""
    query = normalize_selector_text(query)
    target = normalize_selector_text(target)

    if not query or not target:
        return 0.0

    # Exact match
    if query == target:
        return 1.0

    # Contains match
    if query in target:
        return 0.8

    # Word overlap
    query_words = set(query.split())
    target_words = set(target.split())

    if not query_words:
        return 0.0

    overlap = len(query_words & target_words)
    return overlap / len(query_words) * 0.6


def compress_history(steps: list[dict], max_steps: int = 5) -> str:
    """Compress history steps into a summary string."""
    if not steps:
        return "No previous steps."

    # Keep last N steps in detail
    recent = steps[-max_steps:]
    older = steps[:-max_steps] if len(steps) > max_steps else []

    parts = []

    if older:
        # Summarize older steps
        actions = [s.get("action", "unknown") for s in older]
        parts.append(f"Earlier: {len(older)} steps ({', '.join(set(actions))})")

    # Detail recent steps
    for i, step in enumerate(recent):
        action = step.get("action", "unknown")
        result = step.get("result_summary", "")
        parts.append(f"Step {len(steps) - len(recent) + i + 1}: {action} -> {result}")

    return "\n".join(parts)
