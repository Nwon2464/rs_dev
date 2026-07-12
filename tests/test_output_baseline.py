"""Regression tests that freeze the stage-0 generated outputs."""

from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "baselines" / "output_baseline.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def csv_data_rows(relative_path: str) -> int:
    with (ROOT / relative_path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


class OutputBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    def test_output_bytes_match_frozen_baseline(self) -> None:
        for relative_path, expected in self.baseline["files"].items():
            with self.subTest(path=relative_path):
                path = ROOT / relative_path
                self.assertTrue(path.is_file(), f"missing baseline output: {relative_path}")
                data = path.read_bytes()
                self.assertEqual(expected["bytes"], len(data))
                self.assertEqual(expected["sha256"], sha256(data))

    def test_csv_shapes_match_frozen_baseline(self) -> None:
        csv_files = {
            path: expected
            for path, expected in self.baseline["files"].items()
            if path.endswith(".csv")
        }
        for relative_path, expected in csv_files.items():
            with self.subTest(path=relative_path):
                with (ROOT / relative_path).open(
                    encoding="utf-8-sig", newline=""
                ) as handle:
                    reader = csv.reader(handle)
                    header = next(reader, [])
                    data_rows = sum(1 for _ in reader)
                self.assertEqual(expected["columns"], len(header))
                self.assertEqual(expected["data_rows"], data_rows)

    def test_key_data_counts_match_frozen_baseline(self) -> None:
        expected = self.baseline["key_counts"]
        dataset = json.loads(
            (ROOT / "data/processed/instandard_equipment.json").read_text(
                encoding="utf-8"
            )
        )
        trace = json.loads(
            (ROOT / "data/processed/converter_data_trace.json").read_text(
                encoding="utf-8"
            )
        )
        tiers = [tier for option in dataset["options"] for tier in option["tiers"]]
        actual = {
            "instandard_equipment_groups": len(dataset["equipment"]),
            "instandard_option_definitions": len(dataset["options"]),
            "instandard_selectable_options": sum(
                option["selectable"] for option in dataset["options"]
            ),
            "instandard_raw_selectable_options": dataset["summary"][
                "raw_selectable_option_count"
            ],
            "instandard_prefixes": len(dataset["prefix_tag_names"]),
            "instandard_active_tier_rows": sum(
                len(tier["roll_values"]) for tier in tiers if tier["enabled"]
            ),
            "instandard_inactive_tier_rows": sum(
                len(tier["roll_values"]) for tier in tiers if not tier["enabled"]
            ),
            "instandard_render_rows": csv_data_rows(
                "data/processed/instandard_equipment_render_rows.csv"
            ),
            "equipment_converter_rows": csv_data_rows(
                "data/processed/equipment_converter_type_options.csv"
            ),
            "converter_trace_capa_effects": len(trace["capa_converter_effects"]),
            "converter_trace_item_strings": len(trace["item_dat_converter_strings"]),
            "converter_trace_item_effect_ids": len(trace["item_dat_effect_ids"]),
            "converter_trace_open_blocks": len(trace["item_option_open_blocks"]),
        }
        self.assertEqual(expected, actual)

    def test_react_public_data_matches_processed_outputs(self) -> None:
        for name in (
            "instandard_equipment.json",
            "equipment_converter_type_options.csv",
            "instandard_open_option_rows.csv",
            "option_tags.json",
        ):
            with self.subTest(name=name):
                processed = ROOT / "data" / "processed" / name
                public = ROOT / "web" / "public" / "data" / name
                self.assertTrue(public.is_file(), f"missing React public data: {name}")
                self.assertEqual(sha256(processed.read_bytes()), sha256(public.read_bytes()))


if __name__ == "__main__":
    unittest.main()
