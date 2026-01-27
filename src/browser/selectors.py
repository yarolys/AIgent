"""Dynamic selector generation without hardcoded selectors."""

from typing import Any


def generate_unique_selector(element_info: dict[str, Any]) -> str:
    """
    Generate a unique CSS selector for an element dynamically.

    Priority:
    1. Stable attributes: data-testid, data-qa, aria-label, name, id (if unique)
    2. Role + text combination
    3. CSS path with nth-of-type
    4. Tag + text combination
    5. Bounding box position (last resort)

    IMPORTANT: No hardcoded selectors - everything is computed from element properties.
    NEVER returns empty string - always returns something usable.
    """
    # Try stable attributes first
    stable_attrs = ["data-testid", "data-qa", "data-test", "aria-label", "name"]

    for attr in stable_attrs:
        if attr in element_info.get("attributes", {}):
            value = element_info["attributes"][attr]
            if value and value.strip():
                # Escape special characters in attribute value
                escaped_value = _escape_css_value(value.strip())
                return f'[{attr}="{escaped_value}"]'

    # Try id if it looks stable (not auto-generated)
    elem_id = element_info.get("id", "")
    if elem_id and _is_stable_id(elem_id):
        return f"#{_escape_css_id(elem_id)}"

    # Try ariaLabel directly (not nested in attributes)
    aria_label = element_info.get("ariaLabel", "")
    if aria_label and aria_label.strip():
        escaped_label = _escape_css_value(aria_label.strip()[:50])
        return f'[aria-label="{escaped_label}"]'

    # Try role + accessible name combination
    role = element_info.get("role", "")
    name = element_info.get("ariaLabel", "") or element_info.get("accessible_name", "")
    if role and name and name.strip():
        escaped_name = _escape_css_value(name.strip()[:50])
        return f'[role="{role}"][aria-label="{escaped_name}"]'

    # Try placeholder for inputs
    placeholder = element_info.get("placeholder", "")
    if placeholder and placeholder.strip():
        escaped_ph = _escape_css_value(placeholder.strip()[:50])
        return f'[placeholder="{escaped_ph}"]'

    # Build CSS path from ancestors (cssPath from JS, camelCase)
    css_path = element_info.get("cssPath", "") or element_info.get("css_path", "")
    if css_path and css_path.strip():
        return css_path.strip()

    # Fallback: tag + text content selector (using Playwright :has-text)
    tag = element_info.get("tag", "").lower()
    text = element_info.get("text", "")

    if tag and text and text.strip():
        # Clean and limit text
        clean_text = text.strip()[:40]
        if clean_text:
            escaped_text = _escape_css_value(clean_text)
            return f'{tag}:has-text("{escaped_text}")'

    # Try just the tag with type for inputs
    if tag == "input":
        input_type = element_info.get("attributes", {}).get("type", "text")
        return f'input[type="{input_type}"]'

    # Try name attribute if present
    name_attr = element_info.get("name", "")
    if name_attr and name_attr.strip():
        return f'[name="{_escape_css_value(name_attr.strip())}"]'

    # If we have tag, return it
    if tag:
        return tag

    # Last resort: use xpath from element
    xpath = element_info.get("xpath", "")
    if xpath:
        return f"xpath={xpath}"

    # Ultimate fallback - use bounding box position if available
    bbox = element_info.get("bbox", {})
    if bbox and bbox.get("x") is not None and bbox.get("y") is not None:
        # Return a description that can help identify the element
        return f"POSITION_FALLBACK:({bbox.get('x')},{bbox.get('y')})"

    return element_info.get("fallback_selector", "body")


def build_css_path(ancestors: list[dict[str, Any]], max_depth: int = 4) -> str:
    """
    Build a CSS path from ancestor chain.

    Example: div.container > ul.menu > li:nth-of-type(3) > a
    """
    if not ancestors:
        return ""

    # Take last N ancestors (closest to element)
    path_parts = []

    for ancestor in ancestors[-max_depth:]:
        tag = ancestor.get("tag", "div").lower()
        classes = ancestor.get("classes", [])
        nth = ancestor.get("nth_of_type", 1)

        part = tag

        # Add first meaningful class if exists
        if classes:
            # Filter out utility/generated classes
            meaningful_classes = [
                c for c in classes
                if not _is_utility_class(c) and len(c) < 30
            ]
            if meaningful_classes:
                part += f".{meaningful_classes[0]}"

        # Add nth-of-type for disambiguation
        if nth > 1:
            part += f":nth-of-type({nth})"

        path_parts.append(part)

    return " > ".join(path_parts)


def build_xpath(ancestors: list[dict[str, Any]], max_depth: int = 4) -> str:
    """
    Build an XPath from ancestor chain.

    Example: //div[@class='container']/ul/li[3]/a
    """
    if not ancestors:
        return ""

    path_parts = []

    for ancestor in ancestors[-max_depth:]:
        tag = ancestor.get("tag", "div").lower()
        nth = ancestor.get("nth_of_type", 1)

        if nth > 1:
            part = f"{tag}[{nth}]"
        else:
            part = tag

        path_parts.append(part)

    return "//" + "/".join(path_parts)


def _escape_css_value(value: str) -> str:
    """Escape special characters in CSS attribute value."""
    # Escape quotes and backslashes
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    value = value.replace("\n", " ")
    return value


def _escape_css_id(id_value: str) -> str:
    """Escape special characters in CSS ID selector."""
    # IDs starting with numbers need escaping
    if id_value and id_value[0].isdigit():
        id_value = f"\\3{id_value[0]} {id_value[1:]}"
    return id_value.replace(":", "\\:")


def _is_stable_id(id_value: str) -> bool:
    """Check if an ID looks stable (not auto-generated)."""
    # Skip IDs that look auto-generated
    if not id_value:
        return False

    # Common patterns for auto-generated IDs
    auto_patterns = [
        "react-", "ember", "vue-", ":r", ":R",  # Framework prefixes
        "uid-", "id-", "el-",  # Generic prefixes
    ]

    for pattern in auto_patterns:
        if pattern in id_value:
            return False

    # Skip IDs that are mostly numbers/hex
    alphanumeric = sum(1 for c in id_value if c.isalnum())
    numeric = sum(1 for c in id_value if c.isdigit())

    if alphanumeric > 0 and numeric / alphanumeric > 0.5:
        return False

    return True


def _is_utility_class(class_name: str) -> bool:
    """Check if a class looks like a utility/generated class."""
    # Common utility class patterns
    utility_patterns = [
        "css-",  # CSS-in-JS
        "sc-",  # styled-components
        "emotion-",
        "jsx-",
        "svelte-",
        "__",  # BEM modifiers often less stable
    ]

    for pattern in utility_patterns:
        if class_name.startswith(pattern):
            return True

    # Very short or very long classes are often utilities
    if len(class_name) < 2 or len(class_name) > 40:
        return True

    # Classes with lots of numbers
    if sum(1 for c in class_name if c.isdigit()) > len(class_name) / 2:
        return True

    return False
