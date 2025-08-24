import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def linkify(text):
    """
    Convert link markers in text to clickable HTML links.

    Supports the following formats:
    - [text](url) - Markdown-style links
    - [url] - Simple URL in brackets
    - http://example.com or https://example.com - Bare URLs

    Examples:
    - "Check out [this awesome site](https://example.com) for more info"
    - "Visit [https://example.com] to learn more"
    - "Go to https://example.com"
    """
    if not text:
        return text

    # Pattern for markdown-style links: [text](url)
    markdown_pattern = r"\[([^\]]+)\]\(([^)]+)\)"

    # Pattern for simple bracketed URLs: [url]
    bracket_pattern = r"\[([^]]*https?://[^]]+)\]"

    # Pattern for bare URLs
    url_pattern = r'(?<![\["\'>])(https?://[^\s<>"\']+)(?![\]"\'<])'

    # Replace markdown-style links first
    text = re.sub(
        markdown_pattern,
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )

    # Replace bracketed URLs
    text = re.sub(
        bracket_pattern,
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )

    # Replace bare URLs (but not those already processed)
    text = re.sub(
        url_pattern,
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )

    return mark_safe(text)


@register.filter
def linkify_simple(text):
    """
    A simpler version that only handles a custom link marker format: {text|url}

    Example: "Check out {this awesome site|https://example.com} for more info"
    """
    if not text:
        return text

    # Pattern for custom format: {text|url}
    pattern = r"\{([^|]+)\|([^}]+)\}"
    replacement = r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>'

    result = re.sub(pattern, replacement, text)
    return mark_safe(result)
