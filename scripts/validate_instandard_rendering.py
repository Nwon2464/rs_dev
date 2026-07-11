#!/usr/bin/env python3
"""Statically validate the combined HTML's embedded rendering data."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "equipment_options_viewer.html"


def extract(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.S)
    if not match:
        raise ValueError(f"could not extract {label}")
    return match.group(1)


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    pages = json.loads(
        extract(r"const pages = (.*?);\n    const frames", html, "combined pages")
    )
    if set(pages) != {"open", "instandard"}:
        raise ValueError(f"unexpected combined pages: {sorted(pages)}")

    open_rows = json.loads(
        extract(r"const rows = (.*?);\n    const CONVERTER_ORDER", pages["open"], "open rows")
    )
    dataset = json.loads(
        extract(
            r"const dataset = (.*?);\n    const \$",
            pages["instandard"],
            "non-standard dataset",
        )
    )
    if dataset["source_csv"] != "data/processed/instandard_equipment_render_rows.csv":
        raise ValueError("combined HTML is not sourced from the pre-render CSV")

    equipment = {item["item_group_name"]: item for item in dataset["equipment"]}
    if len(equipment) != 34:
        raise ValueError(f"unexpected equipment count={len(equipment)}")
    glove = equipment["장갑"]
    options = {option["option_id"]: option for option in glove["options"]}
    necklace_options = {
        option["option_id"]: option for option in equipment["목걸이"]["options"]
    }
    for option_id in (922, 1045):
        option = necklace_options.get(option_id)
        if not option or option["assignment_basis"] != "supplemental_local_cross_reference":
            raise ValueError(f"supplemental necklace option missing: {option_id}")
    advanced = options[464]
    if [group["raw_tier_index"] for group in advanced["groups"]] != list(range(7)):
        raise ValueError("advanced raw tier sequence mismatch")
    if [group["group_index"] for group in advanced["groups"]] != list(range(3, 10)):
        raise ValueError("advanced common group sequence mismatch")

    observation = {
        460: (95, 1),
        722: (17, 5),
        755: (46, 4),
        462: (32, 3),
        74: (34, 2),
    }
    for option_id, (value, group_index) in observation.items():
        group = next(
            group
            for group in options[option_id]["groups"]
            if group["group_index"] == group_index
        )
        if value not in [vector[0] for vector in group["rolls"]]:
            raise ValueError(f"observed glove value missing for option {option_id}")

    required_ui_terms = (
        "옵션 분류",
        "가능 수치",
        "candidateValues(option)",
        "value-chip",
        "수치 범위",
        "rangeLabel(option)",
        "candidateDialog",
        "range-button",
    )
    missing_terms = [term for term in required_ui_terms if term not in pages["instandard"]]
    if missing_terms:
        raise ValueError(f"missing rendering terms: {missing_terms}")
    hidden_ui_terms = (
        "공통 수치 구간",
        'id="groupFilters"',
        "OptionLevel",
        "후보 수치",
    )
    exposed_terms = [term for term in hidden_ui_terms if term in pages["instandard"]]
    if exposed_terms:
        raise ValueError(f"internal terms exposed in user UI: {exposed_terms}")

    print(
        json.dumps(
            {
                "status": "ok",
                "combined_html": str(HTML.relative_to(ROOT)),
                "open_option_rows": len(open_rows),
                "nonstandard_equipment_groups": len(equipment),
                "glove_options": len(glove["options"]),
                "necklace_options": len(necklace_options),
                "advanced_464_raw_to_common": [
                    [group["raw_tier_index"], group["group_index"]]
                    for group in advanced["groups"]
                ],
                "glove_observation_values_checked": len(observation),
                "browser_interaction_checked": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
