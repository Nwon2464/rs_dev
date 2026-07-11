#!/usr/bin/env python3
"""CLI for extracting damage-related capa.dat evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "damage_experiment"
sys.path[:0] = [str(ROOT / "src"), str(EXPERIMENT / "src")]

from damage_experiment.capa_evidence import (  # noqa: E402
    extract_damage_capa_evidence,
    write_evidence,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capa", type=Path, default=ROOT / "data/raw/capa.dat")
    parser.add_argument(
        "--buckets",
        type=Path,
        default=EXPERIMENT / "notes/damage_buckets.md",
    )
    parser.add_argument("--client-version", required=True)
    parser.add_argument("--collected-at")
    parser.add_argument(
        "--output",
        type=Path,
        default=EXPERIMENT / "data/evidence/damage_capa_evidence.json",
    )
    args = parser.parse_args()

    evidence = extract_damage_capa_evidence(
        args.capa,
        args.buckets,
        client_version=args.client_version,
        collected_at=args.collected_at,
    )
    write_evidence(args.output, evidence)
    print(f"wrote {len(evidence)} Capa evidence records to {args.output}")


if __name__ == "__main__":
    main()

