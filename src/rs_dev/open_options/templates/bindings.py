"""Load explicit option-specific value-index bindings."""

from __future__ import annotations

import json
from pathlib import Path


def load_value_bindings(path: Path) -> dict[int, dict[int, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        int(option_id): {int(target): int(source) for target, source in bindings.items()}
        for option_id, bindings in payload.items()
    }
