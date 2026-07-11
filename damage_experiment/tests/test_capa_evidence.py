from __future__ import annotations

import json
from pathlib import Path

from damage_experiment.capa_evidence import (
    HEADER_NAMES,
    extract_damage_capa_evidence,
    load_bucket_definitions,
    write_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "damage_experiment"


def test_bucket_notes_define_only_numeric_capa_ids() -> None:
    definitions = load_bucket_definitions(EXPERIMENT / "notes/damage_buckets.md")
    assert {52, 460, 724, 984, 1034, 1035} <= set(definitions)
    assert all(row["bucket_evidence_level"] == "confirmed" for row in definitions.values())


def test_extracts_headers_strings_and_writes_json(tmp_path: Path) -> None:
    evidence = extract_damage_capa_evidence(
        ROOT / "data/raw/capa.dat",
        EXPERIMENT / "notes/damage_buckets.md",
        client_version="884",
        collected_at="2026-07-11",
    )
    assert evidence
    assert [row["subject_id"] for row in evidence] == sorted(
        row["subject_id"] for row in evidence
    )
    for row in evidence:
        assert row["evidence_level"] == "confirmed"
        assert row["source_file"] == "capa.dat"
        assert row["client_version"] == "884"
        assert row["header_fields"]["option_id"] == row["subject_id"]
        assert tuple(row["header_fields"]) == HEADER_NAMES
        assert "limit_candidate" in row["header_fields"]
        assert row["strings"]["name"]

    output = tmp_path / "evidence.json"
    write_evidence(output, evidence)
    assert json.loads(output.read_text(encoding="utf-8")) == evidence

