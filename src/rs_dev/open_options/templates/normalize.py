"""Conservative normalization shared by generated locale catalogs."""

from __future__ import annotations


def normalize_template(template: str) -> str:
    """Normalize surrounding whitespace without rewriting source wording."""
    return template.strip()
