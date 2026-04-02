"""
Text preprocessing and cleaning utilities.
"""

import re
import logging

logger = logging.getLogger("privategpt.processor")


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text:
    - Remove excessive whitespace
    - Fix encoding artifacts
    - Normalize line breaks
    - Remove control characters
    """
    if not text:
        return ""

    # Remove null bytes and control characters (keep newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Fix common encoding artifacts
    replacements = {
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--',
        '\u2026': '...',
        '\u00a0': ' ',  # Non-breaking space
        '\ufeff': '',   # BOM
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize whitespace: collapse multiple spaces, preserve paragraph breaks
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs → single space
    text = re.sub(r'\n{3,}', '\n\n', text)  # 3+ newlines → 2
    text = re.sub(r' +\n', '\n', text)  # Trailing spaces before newline

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def extract_title(text: str, max_length: int = 200) -> str:
    """Extract a probable title from the first meaningful line."""
    for line in text.split('\n'):
        line = line.strip()
        if len(line) > 5 and not line.startswith(('http', 'www', '#', '//')):
            return line[:max_length]
    return "Untitled"
