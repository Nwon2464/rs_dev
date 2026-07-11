"""Extract damage-related capa.dat records as read-only evidence."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from rs_dev.parsers import parse_capa, u32


EVIDENCE_LEVELS = {"confirmed", "inferred", "unknown"}
HEADER_NAMES = (
    "option_id",
    "category",
    "limit_candidate",
    "field_3",
    "field_4",
    "field_5",
    "field_6",
    "field_7",
)


def load_bucket_definitions(path: Path) -> dict[int, dict[str, str]]:
    definitions: dict[int, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        bucket, raw_ids, _, raw_level, _ = cells
        level = raw_level.strip("`")
        if level not in EVIDENCE_LEVELS or raw_ids == "해당 없음":
            continue
        for part in (value.strip() for value in raw_ids.split(",")):
            match = re.fullmatch(r"(\d+)(?:~(\d+))?", part)
            if not match:
                raise ValueError(f"invalid Capa ID specification: {part}")
            start = int(match.group(1))
            end = int(match.group(2) or start)
            for option_id in range(start, end + 1):
                if option_id in definitions:
                    raise ValueError(f"duplicate Capa ID in bucket notes: {option_id}")
                definitions[option_id] = {
                    "bucket": bucket,
                    "bucket_evidence_level": level,
                }
    if not definitions:
        raise ValueError(f"no damage Capa IDs found in {path}")
    return definitions


def extract_damage_capa_evidence(
    capa_path: Path,
    bucket_path: Path,
    *,
    client_version: str,
    collected_at: str | None = None,
) -> list[dict[str, Any]]:
    if not client_version.strip():
        raise ValueError("client_version must not be empty")
    definitions = load_bucket_definitions(bucket_path)
    records = parse_capa(capa_path)
    raw = capa_path.read_bytes()
    missing = sorted(set(definitions) - set(records))
    if missing:
        raise ValueError(f"damage Capa IDs missing from capa.dat: {missing}")

    observed_on = collected_at or date.today().isoformat()
    evidence: list[dict[str, Any]] = []
    for option_id in sorted(definitions):
        record = records[option_id]
        offset = int(record["record_offset"])
        header = {
            name: u32(raw, offset + index * 4)
            for index, name in enumerate(HEADER_NAMES)
        }
        evidence.append(
            {
                "evidence_id": f"capa-{option_id}",
                "evidence_level": "confirmed",
                "subject_type": "capa",
                "subject_id": option_id,
                **definitions[option_id],
                "source_file": capa_path.name,
                "source_path": str(capa_path),
                "source_offset": offset,
                "source_offset_hex": hex(offset),
                "source_locator": hex(offset),
                "client_version": client_version,
                "source_version": client_version,
                "collected_at": observed_on,
                "header_fields": header,
                "strings": {
                    "name": record["name"],
                    "description": record["description"],
                    "short_text": record["short_text"],
                    "help_text": record["help_text"],
                },
                "raw_value": header,
                "claim": "capa.dat의 8개 헤더 필드와 문자열을 직접 추출했다. limit_candidate는 실제 상한으로 적용하지 않았다.",
            }
        )
    return evidence


def write_evidence(path: Path, evidence: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

