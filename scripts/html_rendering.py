"""Small, strict helpers shared by the standalone and combined HTML renderers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def json_for_script(value: Any) -> str:
    """Serialize embedded data and keep it from terminating a script element."""
    return "<\\/".join(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).split("</")
    )


def substitute_once(document: str, marker: str, value: str, *, label: str) -> str:
    """Replace one required marker, failing when the template shape has drifted."""
    before, found, after = document.partition(marker)
    if not found:
        raise ValueError(f"missing HTML template marker: {label}")
    if marker in after:
        raise ValueError(f"duplicate HTML template marker: {label}")
    return before + value + after


def substitute_first(document: str, marker: str, value: str, *, label: str) -> str:
    """Replace the first required marker when later copies are intentional."""
    before, found, after = document.partition(marker)
    if not found:
        raise ValueError(f"missing HTML template marker: {label}")
    return before + value + after


def substitute_many(
    document: str, marker: str, value: str, *, count: int, label: str
) -> str:
    """Replace an exact number of repeated markers."""
    parts = document.split(marker)
    actual = len(parts) - 1
    if actual != count:
        raise ValueError(
            f"unexpected HTML template marker count for {label}: {actual} != {count}"
        )
    return value.join(parts)


def remove_optional_block(document: str, start: str, end: str) -> str:
    """Remove one optional block including its end marker."""
    before, found, remainder = document.partition(start)
    if not found:
        return document
    _, closed, after = remainder.partition(end)
    if not closed:
        raise ValueError("unterminated optional HTML template block")
    return before + after


def replace_script(document: str, script: str) -> str:
    """Replace the template's single script element with a rendered script."""
    before, found, remainder = document.partition("<script>")
    if not found:
        raise ValueError("HTML template has no script element")
    _, closed, after = remainder.partition("</script>")
    if not closed:
        raise ValueError("HTML template has an unterminated script element")
    return before + script + after


def read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")
