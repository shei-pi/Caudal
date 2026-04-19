import re
import unicodedata


def normalize_description(text: str) -> str:
    """Uppercase, strip accents and extra whitespace for matching."""
    text = text.upper().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text
