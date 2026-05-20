import html
import re

import bleach


def sanitize_input(text, allow_html=False):
    """Sanitize user input to prevent XSS attacks."""
    if not text:
        return text

    if allow_html:
        allowed_tags = ["b", "i", "u", "em", "strong", "p", "br"]
        return bleach.clean(text, tags=allowed_tags, strip=True)
    return html.escape(str(text))


def validate_email_format(email):
    """Validate email format more rigorously."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None
