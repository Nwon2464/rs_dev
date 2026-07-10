#!/usr/bin/env python3
"""Validate non-standard equipment data before any HTML rendering step."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "data" / "processed" / "instandard_equipment.json"
DEFAULT_RAW_CSV = ROOT / "data" / "processed" / "instandard_equipment_tiers.csv"
DEFAULT_PRE_RENDER_CSV = (
    ROOT / "data" / "processed" / "instandard_equipment_render_rows.csv"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--raw-csv", type=Path, default=DEFAULT_RAW_CSV)
    parser.add_argument(
        "--pre-render-csv", type=Path, default=DEFAULT_PRE_RENDER_CSV
    )
    args = parser.parse_args()

    dataset = json.loads(args.json.read_text(encoding="utf-8"))
    if dataset.get("schema_version") != 2:
        fail(f"unexpected schema_version={dataset.get('schema_version')}")

    data_dir = Path(dataset["source"]["data_dir"])
    for metadata in dataset["source"]["file_metadata"]:
        path = data_dir / metadata["name"]
        if path.stat().st_size != metadata["size"]:
            fail(f"source size changed: {path}")
        if sha256(path) != metadata["sha256"]:
            fail(f"source hash changed: {path}")

    options = {option["option_id"]: option for option in dataset["options"]}
    mapped_ids: set[int] = set()
    for equipment in dataset["equipment"]:
        option_ids = equipment["option_ids"]
        if len(option_ids) != len(set(option_ids)):
            fail(f"duplicate option id in equipment {equipment['item_group_name']}")
        missing = set(option_ids) - set(options)
        if missing:
            fail(f"undefined options in {equipment['item_group_name']}: {missing}")
        mapped_ids.update(option_ids)

    necklace = next(row for row in dataset["equipment"] if row["item_group_id"] == 8)
    if necklace["supplemental_option_ids"] != [1045, 922]:
        fail("necklace supplemental assignment mismatch")
    if any(option_id in necklace["raw_option_ids"] for option_id in (922, 1045)):
        fail("supplemental necklace options unexpectedly present in raw mapping")
    if not all(option_id in necklace["option_ids"] for option_id in (922, 1045)):
        fail("supplemental necklace options missing from effective mapping")

    selectable = {option_id for option_id, row in options.items() if row["selectable"]}
    if selectable != mapped_ids:
        fail(
            f"selectable/mapped mismatch: selectable_only={selectable-mapped_ids}, "
            f"mapped_only={mapped_ids-selectable}"
        )

    level_keys = dataset["summary"]["option_level_keys"]
    if level_keys != sorted(set(level_keys)):
        fail("option_level_keys are not unique and sorted")
    shifted_ids = []
    for option in dataset["options"]:
        shifted = False
        for tier in option["tiers"]:
            if tier["raw_tier_index"] != tier["tier"]:
                fail(f"legacy tier alias mismatch in option {option['option_id']}")
            if not tier["enabled"]:
                if tier["option_level_group_index"] is not None:
                    fail(f"disabled group has index in option {option['option_id']}")
                continue
            group_index = tier["option_level_group_index"]
            if level_keys[group_index] != tier["option_level_raw"]:
                fail(f"OptionLevel group mismatch in option {option['option_id']}")
            expected_offset = group_index - tier["raw_tier_index"]
            if tier["group_index_offset_from_raw_tier"] != expected_offset:
                fail(f"group offset mismatch in option {option['option_id']}")
            shifted |= expected_offset != 0
        if shifted:
            shifted_ids.append(option["option_id"])
    if shifted_ids != dataset["summary"]["shifted_raw_tier_option_ids"]:
        fail("shifted option summary mismatch")

    with args.raw_csv.open(encoding="utf-8", newline="") as handle:
        raw_rows = list(csv.DictReader(handle))
    expected_raw_rows = sum(
        len(tier["roll_values"])
        for option in dataset["options"]
        for tier in option["tiers"]
    )
    if len(raw_rows) != expected_raw_rows:
        fail(f"raw CSV row mismatch: {len(raw_rows)} != {expected_raw_rows}")

    with args.pre_render_csv.open(encoding="utf-8", newline="") as handle:
        pre_render_rows = list(csv.DictReader(handle))
    expected_pre_render_rows = sum(
        sum(tier["enabled"] for tier in options[option_id]["tiers"])
        for equipment in dataset["equipment"]
        for option_id in equipment["option_ids"]
    )
    if len(pre_render_rows) != expected_pre_render_rows:
        fail(
            f"pre-render CSV row mismatch: {len(pre_render_rows)} "
            f"!= {expected_pre_render_rows}"
        )

    for option_id in (922, 1045):
        supplemental_rows = [
            row
            for row in pre_render_rows
            if row["item_group_name"] == "목걸이"
            and int(row["option_id"]) == option_id
        ]
        if len(supplemental_rows) != 7:
            fail(f"supplemental necklace tier count mismatch for {option_id}")
        if any(
            row["assignment_basis"] != "supplemental_local_cross_reference"
            for row in supplemental_rows
        ):
            fail(f"supplemental assignment provenance missing for {option_id}")
        if any("[1" in row["option_template"] for row in supplemental_rows):
            fail(f"combined display template was not normalized for {option_id}")

    # User-observed 1500 glove values, retained as an external structural check.
    glove_observation = {
        460: (95, 1),
        722: (17, 5),
        755: (46, 4),
        462: (32, 3),
        74: (34, 2),
    }
    for option_id, (observed_value, group_index) in glove_observation.items():
        hits = [
            row
            for row in pre_render_rows
            if row["item_group_name"] == "장갑"
            and int(row["option_id"]) == option_id
            and int(row["option_level_group_index"]) == group_index
        ]
        if len(hits) != 1:
            fail(f"glove observation row mismatch for option {option_id}")
        values = [
            int(hits[0][f"roll_{index:02d}_raw"].split("/")[0])
            for index in range(1, 11)
        ]
        if observed_value not in values:
            fail(f"glove observed value missing for option {option_id}")

    print(
        json.dumps(
            {
                "status": "ok",
                "schema_version": dataset["schema_version"],
                "equipment_groups": len(dataset["equipment"]),
                "option_definitions": len(dataset["options"]),
                "necklace_options": len(necklace["option_ids"]),
                "necklace_supplemental_options": necklace["supplemental_option_ids"],
                "option_level_keys": level_keys,
                "shifted_option_ids": shifted_ids,
                "raw_csv_rows": len(raw_rows),
                "pre_render_csv_rows": len(pre_render_rows),
                "html_rendering_checked": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
