"""Collect and join Red Stone's non-standard equipment tables.

The source files are read-only.  The decoder intentionally uses only Python's
standard library because InstandardEquip.dat is MessagePack but the msgpack
package is not guaranteed to be installed in the analysis environment.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any


from rs_dev.parsers import parse_capa, parse_item_groups
from rs_dev.models import (
    InstandardDataset,
    InstandardRenderRow,
    InstandardTierCsvRow,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = Path("/mnt/c/game/Red Stone/Data")
DEFAULT_MARKDOWN = ROOT / "비규격.md"
DEFAULT_JSON = ROOT / "data" / "processed" / "instandard_equipment.json"
DEFAULT_CSV = ROOT / "data" / "processed" / "instandard_equipment_tiers.csv"
DEFAULT_RENDER_CSV = (
    ROOT / "data" / "processed" / "instandard_equipment_render_rows.csv"
)

# OptionData 922/1045 are not present in the raw OptionsByItemType rows. Local
# cross-tables independently connect both effects to item group 8 (necklace),
# so expose them as a provenance-labelled supplement instead of pretending the
# raw MessagePack mapping contains them.
SUPPLEMENTAL_ITEM_GROUP_OPTIONS = {8: [1045, 922]}
SUPPLEMENTAL_ASSIGNMENT_EVIDENCE = {
    1045: {
        "item_group_id": 8,
        "basis": "item.dat fixed-effect references",
        "item_ids": [1390, 5238, 7145, 7432, 7433],
        "item_names": [
            "마도풍",
            "마도풍[Nx]",
            "마도풍[E]",
            "마도풍[R]",
            "마도풍[Nx][R]",
        ],
    },
    922: {
        "item_group_id": 8,
        "basis": "item_option_open.dat equipment target list",
        "item_ids": [],
        "item_names": [],
    },
}


class MessagePackDecoder:
    """Small MessagePack decoder covering every type used by the source file."""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def read(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.data):
            raise ValueError(f"truncated MessagePack value at {self.offset:#x}")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def uint(self, size: int) -> int:
        return int.from_bytes(self.read(size), "big")

    @staticmethod
    def decode_text(raw: bytes) -> str:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("cp949")

    def value(self) -> Any:
        code = self.uint(1)
        if code <= 0x7F:
            return code
        if code >= 0xE0:
            return code - 0x100
        if 0xA0 <= code <= 0xBF:
            return self.decode_text(self.read(code & 0x1F))
        if 0x90 <= code <= 0x9F:
            return [self.value() for _ in range(code & 0x0F)]
        if 0x80 <= code <= 0x8F:
            return {self.value(): self.value() for _ in range(code & 0x0F)}
        if code == 0xC0:
            return None
        if code == 0xC2:
            return False
        if code == 0xC3:
            return True
        if code == 0xCA:
            return struct.unpack(">f", self.read(4))[0]
        if code == 0xCB:
            return struct.unpack(">d", self.read(8))[0]
        if 0xCC <= code <= 0xCF:
            return self.uint((1, 2, 4, 8)[code - 0xCC])
        if 0xD0 <= code <= 0xD3:
            size = (1, 2, 4, 8)[code - 0xD0]
            return int.from_bytes(self.read(size), "big", signed=True)
        if 0xD9 <= code <= 0xDB:
            size = self.uint((1, 2, 4)[code - 0xD9])
            return self.decode_text(self.read(size))
        if code in (0xDC, 0xDD):
            return [self.value() for _ in range(self.uint((2, 4)[code - 0xDC]))]
        if code in (0xDE, 0xDF):
            return {
                self.value(): self.value()
                for _ in range(self.uint((2, 4)[code - 0xDE]))
            }
        if 0xC4 <= code <= 0xC6:
            return self.read(self.uint((1, 2, 4)[code - 0xC4]))
        raise ValueError(f"unsupported MessagePack code {code:#x} at {self.offset - 1:#x}")

    def unpack(self) -> Any:
        result = self.value()
        if self.offset != len(self.data):
            raise ValueError(
                f"trailing MessagePack bytes: decoded={self.offset}, size={len(self.data)}"
            )
        return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact_rolls(values: list[int]) -> str:
    counts = Counter(values)
    if len(counts) == 1:
        value = values[0]
        return f"{value}×{len(values)}"
    if len(counts) != len(values):
        return ", ".join(f"{value}×{counts[value]}" for value in counts)
    steps = [right - left for left, right in zip(values, values[1:])]
    if steps and len(set(steps)) == 1:
        return f"{values[0]}~{values[-1]} (간격 {steps[0]}, {len(values)}개)"
    return ", ".join(map(str, values))


def md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def build_dataset(data_dir: Path) -> dict[str, Any]:
    source = data_dir / "InstandardEquip.dat"
    decoded = MessagePackDecoder(source.read_bytes()).unpack()
    if set(decoded) != {
        "DisJointData",
        "MaterialData",
        "OptionData",
        "OptionsByItemType",
        "PrefixTagName",
    }:
        raise ValueError(f"unexpected top-level fields: {sorted(decoded)}")

    groups = parse_item_groups(data_dir / "simpleGameText.dat")
    capa = parse_capa(data_dir / "capa.dat")
    raw_used_ids = {
        option_id for _, option_ids in decoded["OptionsByItemType"] for option_id in option_ids
    }
    supplemental_ids = {
        option_id
        for option_ids in SUPPLEMENTAL_ITEM_GROUP_OPTIONS.values()
        for option_id in option_ids
    }
    used_ids = raw_used_ids | supplemental_ids

    options = []
    for raw in decoded["OptionData"]:
        option_id = raw["OptionCapaIndex"]
        if option_id not in capa:
            raise ValueError(f"OptionCapaIndex={option_id} is missing from capa.dat")
        tiers = []
        for tier in raw["TierData"]:
            vectors = tier["TierValue"]
            if len(vectors) != 10 or any(len(vector) != 3 for vector in vectors):
                raise ValueError(f"unexpected TierValue shape for option_id={option_id}")
            tiers.append(
                {
                    "tier": tier["Tier"],
                    "raw_tier_index": tier["Tier"],
                    "option_level_raw": tier["OptionLevel"],
                    "enabled": tier["OptionLevel"] != 99999,
                    "roll_values": vectors,
                }
            )
        options.append(
            {
                "option_id": option_id,
                "name": capa[option_id]["name"],
                "description": capa[option_id]["description"],
                "short_text": capa[option_id]["short_text"],
                "tags": raw["TagName"],
                "selectable": option_id in used_ids,
                "raw_selectable": option_id in raw_used_ids,
                "supplemental_assignment": SUPPLEMENTAL_ASSIGNMENT_EVIDENCE.get(option_id),
                "tiers": tiers,
            }
        )

    option_level_keys = sorted(
        {
            tier["option_level_raw"]
            for option in options
            for tier in option["tiers"]
            if tier["enabled"]
        }
    )
    option_level_group = {value: index for index, value in enumerate(option_level_keys)}
    for option in options:
        for tier in option["tiers"]:
            group_index = (
                option_level_group[tier["option_level_raw"]]
                if tier["enabled"]
                else None
            )
            tier["option_level_group_index"] = group_index
            tier["option_level_group_number"] = (
                group_index + 1 if group_index is not None else None
            )
            tier["group_index_offset_from_raw_tier"] = (
                group_index - tier["raw_tier_index"]
                if group_index is not None
                else None
            )

    option_map = {row["option_id"]: row for row in options}
    equipment = []
    for group_id, raw_option_ids in decoded["OptionsByItemType"]:
        if group_id not in groups:
            raise ValueError(f"unknown item group id {group_id}")
        option_ids = [
            *raw_option_ids,
            *SUPPLEMENTAL_ITEM_GROUP_OPTIONS.get(group_id, []),
        ]
        missing = [option_id for option_id in option_ids if option_id not in option_map]
        if missing:
            raise ValueError(f"item group {group_id} has undefined options: {missing}")
        equipment.append(
            {
                "item_group_id": group_id,
                "item_group_name": groups[group_id],
                "option_ids": option_ids,
                "raw_option_ids": raw_option_ids,
                "supplemental_option_ids": SUPPLEMENTAL_ITEM_GROUP_OPTIONS.get(group_id, []),
            }
        )

    revision = {}
    revision_path = data_dir / "RevisionInfo.txt"
    if revision_path.exists():
        for line in revision_path.read_text(encoding="ascii", errors="replace").splitlines():
            parts = line.split()
            if len(parts) == 2:
                revision[parts[0]] = parts[1]

    mechanics = {
        option_id: capa[option_id]
        for option_id in (1062, 1063, 1064, 1065, 1066, 1067, 1069)
    }
    source_files = [
        "InstandardEquip.dat",
        "simpleGameText.dat",
        "capa.dat",
        "item.dat",
        "item_option_open.dat",
        "title.dat",
        "RevisionInfo.txt",
    ]
    shifted_option_ids = [
        option["option_id"]
        for option in options
        if any(
            tier["enabled"]
            and tier["option_level_group_index"] != tier["raw_tier_index"]
            for tier in option["tiers"]
        )
    ]
    dataset = {
        "schema_version": 2,
        "generator": "scripts/collect_instandard_equipment.py",
        "source": {
            "data_dir": str(data_dir),
            "files": source_files,
            "file_metadata": [
                {
                    "name": name,
                    "size": (data_dir / name).stat().st_size,
                    "sha256": sha256(data_dir / name),
                }
                for name in source_files
                if (data_dir / name).exists()
            ],
            "revision": revision,
        },
        "summary": {
            "equipment_group_count": len(equipment),
            "option_definition_count": len(options),
            "selectable_option_count": len(used_ids),
            "raw_selectable_option_count": len(raw_used_ids),
            "supplemental_option_ids": sorted(supplemental_ids),
            "unused_option_ids": sorted(set(option_map) - used_ids),
            "prefix_count": len(decoded["PrefixTagName"]),
            "option_level_keys": option_level_keys,
            "shifted_raw_tier_option_ids": shifted_option_ids,
        },
        "equipment": equipment,
        "options": options,
        "prefix_tag_names": decoded["PrefixTagName"],
        "material_data": decoded["MaterialData"],
        "disjoint_data": decoded["DisJointData"],
        "mechanics_capa": mechanics,
        "supplemental_assignments": SUPPLEMENTAL_ASSIGNMENT_EVIDENCE,
    }
    InstandardDataset.model_validate(dataset)
    return dataset


def write_csv(path: Path, dataset: dict[str, Any]) -> None:
    equipment_by_option: dict[int, list[str]] = {}
    for equipment in dataset["equipment"]:
        for option_id in equipment["option_ids"]:
            equipment_by_option.setdefault(option_id, []).append(equipment["item_group_name"])

    rows = []
    for option in dataset["options"]:
        for tier in option["tiers"]:
            for roll_index, vector in enumerate(tier["roll_values"]):
                rows.append(
                    {
                        "option_id": option["option_id"],
                        "option_name": option["name"],
                        "short_text": option["short_text"],
                        "tags": "/".join(option["tags"]),
                        "selectable": option["selectable"],
                        "raw_selectable": option["raw_selectable"],
                        "assignment_basis": (
                            "supplemental_local_cross_reference"
                            if option["supplemental_assignment"]
                            else "InstandardEquip.OptionsByItemType"
                        ),
                        "equipment_groups": ",".join(
                            equipment_by_option.get(option["option_id"], [])
                        ),
                        "tier": tier["tier"],
                        "raw_tier_index": tier["raw_tier_index"],
                        "option_level_raw": tier["option_level_raw"],
                        "option_level_group_index": tier[
                            "option_level_group_index"
                        ],
                        "option_level_group_number": tier[
                            "option_level_group_number"
                        ],
                        "group_index_offset_from_raw_tier": tier[
                            "group_index_offset_from_raw_tier"
                        ],
                        "enabled": tier["enabled"],
                        "roll_index": roll_index,
                        "value_0": vector[0],
                        "value_1": vector[1],
                        "value_2": vector[2],
                    }
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    if list(InstandardTierCsvRow.model_fields) != fieldnames:
        raise ValueError("non-standard tier model field order differs from CSV schema")
    for row in rows:
        InstandardTierCsvRow.model_validate(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


VALUE_TOKEN = re.compile(r"\[([012])(?:\.(\d+))?([%％])?\]")


def render_option_value(template: str, vector: list[int]) -> str:
    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        digits = int(match.group(2) or 0)
        suffix = match.group(3) or ""
        value = vector[index]
        rendered = str(value) if not digits else f"{value / 10**digits:.{digits}f}"
        return rendered + suffix

    return VALUE_TOKEN.sub(replace, template)


def display_template(option_id: int, template: str) -> str:
    """Use the single OptionData roll for both clauses of combined effects."""
    if option_id in (922, 1045):
        return template.replace("[1]", "[0]").replace("[1.1%]", "[0.1%]")
    return template


def write_render_csv(path: Path, dataset: dict[str, Any]) -> int:
    """Write enabled equipment × option × global OptionLevel-group rows."""
    option_map = {option["option_id"]: option for option in dataset["options"]}
    rows: list[dict[str, Any]] = []
    for equipment in dataset["equipment"]:
        for option_order, option_id in enumerate(equipment["option_ids"], start=1):
            option = option_map[option_id]
            template = display_template(
                option_id, option["short_text"] or option["description"]
            )
            supplemental = option_id in equipment["supplemental_option_ids"]
            for tier in option["tiers"]:
                if not tier["enabled"]:
                    continue
                vectors = tier["roll_values"]
                displays = [render_option_value(template, vector) for vector in vectors]
                value_0 = [vector[0] for vector in vectors]
                row: dict[str, Any] = {
                    "item_group_id": equipment["item_group_id"],
                    "item_group_name": equipment["item_group_name"],
                    "option_order_in_equipment": option_order,
                    "option_id": option_id,
                    "option_name": option["name"],
                    "option_template": template,
                    "tags": "/".join(option["tags"]),
                    "assignment_basis": (
                        "supplemental_local_cross_reference"
                        if supplemental
                        else "InstandardEquip.OptionsByItemType"
                    ),
                    "raw_tier_index": tier["raw_tier_index"],
                    "option_level_raw": tier["option_level_raw"],
                    "option_level_group_index": tier["option_level_group_index"],
                    "option_level_group_number": tier["option_level_group_number"],
                    "group_index_offset_from_raw_tier": tier[
                        "group_index_offset_from_raw_tier"
                    ],
                    "value_0_min": min(value_0),
                    "value_0_max": max(value_0),
                    "display_min": displays[value_0.index(min(value_0))],
                    "display_max": displays[value_0.index(max(value_0))],
                    "roll_vectors_json": json.dumps(vectors, separators=(",", ":")),
                    "display_rolls_json": json.dumps(
                        displays, ensure_ascii=False, separators=(",", ":")
                    ),
                    "mapping_basis": (
                        "local item.dat/item_option_open.dat cross-reference"
                        if supplemental
                        else "InstandardEquip.OptionsByItemType"
                    ) + " + OptionData.OptionLevel + simpleGameText + capa",
                }
                for roll_index, (vector, display) in enumerate(
                    zip(vectors, displays), start=1
                ):
                    row[f"roll_{roll_index:02d}_raw"] = "/".join(map(str, vector))
                    row[f"roll_{roll_index:02d}_display"] = display
                rows.append(row)

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    if list(InstandardRenderRow.model_fields) != fieldnames:
        raise ValueError("non-standard render model field order differs from CSV schema")
    for row in rows:
        InstandardRenderRow.model_validate(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def markdown(dataset: dict[str, Any]) -> str:
    summary = dataset["summary"]
    option_map = {row["option_id"]: row for row in dataset["options"]}
    option_level_keys = sorted(
        {
            tier["option_level_raw"]
            for option in dataset["options"]
            for tier in option["tiers"]
            if tier["enabled"]
        }
    )
    option_level_group = {value: index for index, value in enumerate(option_level_keys)}
    shifted_options = [
        option
        for option in dataset["options"]
        if any(
            tier["enabled"]
            and option_level_group[tier["option_level_raw"]] != tier["tier"]
            for tier in option["tiers"]
        )
    ]
    equipment_by_option: dict[int, list[str]] = {}
    for equipment in dataset["equipment"]:
        for option_id in equipment["option_ids"]:
            equipment_by_option.setdefault(option_id, []).append(equipment["item_group_name"])

    lines = [
        "# 비규격 장비 데이터 조사",
        "",
        "## 결론",
        "",
        f"`InstandardEquip.dat`는 비규격 장비 전용 MessagePack 테이블이다. 장비군 {summary['equipment_group_count']}개, 옵션 정의 {summary['option_definition_count']}개를 확인했다. 원본 `OptionsByItemType` 직접 연결은 {summary['raw_selectable_option_count']}개이며, 로컬 교차검증으로 목걸이에 보완한 922·1045를 포함하면 화면 후보는 {summary['selectable_option_count']}개다.",
        "",
        "각 옵션의 원본 `TierData`에는 `Tier=0..9` 그룹과 그룹별 10개 이산 수치가 있다. 현재 파일의 모든 `TierValue`는 `[value0, 0, 0]` 형태이므로 표시문의 `[수치]0`에 `value0`을 넣으면 된다. 이 `Tier`가 게임에 노출되는 정식 티어인지 내부 수치 구간인지는 확정하지 않았고, `OptionLevel`의 산식도 원시값으로 보존했다.",
        "",
        "1250·1500·1750은 베이스 장비의 요구 레벨이며 원본 `TierData` 그룹과는 별개다. 외부 운영 참고 자료는 수치 재설정이 동일 Tier 안에서 이루어진다고 설명하지만, 로컬 DAT에는 실제 추첨 순서나 게임 화면의 티어 표시를 연결하는 레코드가 없으므로 내부 그룹 해석과 구분한다.",
        "",
        "`OptionLevel=99999`인 티어는 고급 옵션 일부에서 남은 칸을 채우며 수치도 `999` 또는 `99999`로 반복된다. 실제 획득 수치가 아니라 비활성 센티널로 보는 것이 타당하며, 아래 유효 범위와 렌더링에서는 제외했다. 이는 구조 패턴에 근거한 해석이다.",
        "",
        "## 출처와 재현",
        "",
        "- 원본 폴더: `C:\\game\\Red Stone\\Data` (현재 환경의 `/mnt/c/game/Red Stone/Data`)",
        f"- 리비전: `{dataset['source']['revision'].get('Client', '?')}`, 클라이언트 버전: `{dataset['source']['revision'].get('Client_Version', '?')}`",
        "- 핵심 구조: `InstandardEquip.dat` → 장비별 옵션 ID·티어·수치·태그·접두 문구·재료 레코드",
        "- 명칭 조인: `simpleGameText.dat` → 장비군 ID, `capa.dat` → 옵션 ID·표시문·시스템 동작",
        "- 생성 명령: `python3 scripts/collect_instandard_equipment.py`",
        "- 구조 검증: `python3 scripts/validate_instandard_equipment.py`",
        "- React 공개 데이터·웹 빌드: `cd web && npm run build:all`",
        "- 기계 판독용 결과: `data/processed/instandard_equipment.json`, `data/processed/instandard_equipment_tiers.csv`",
        "- 렌더링 직전 장비별 결과: `data/processed/instandard_equipment_render_rows.csv`",
        "",
        "```text",
        "simpleGameText.item_group_id ─┐",
        "                               ├─ OptionsByItemType ─ option_id ─┐",
        "InstandardEquip.OptionData ────┘                                ├─ 장비별 비규격 옵션",
        "capa.option_id ─────────────────────────────────────────────────┘",
        "```",
        "",
        "## 목걸이 보완 옵션 922·1045",
        "",
        "원본 `InstandardEquip.OptionsByItemType`에는 922·1045가 없지만, 같은 로컬 Data 폴더의 독립 테이블에서 두 효과 모두 장비군 8(목걸이)과 연결된다. 화면에서는 두 옵션을 목걸이에 추가하되 `로컬 교차검증 보완`으로 표시하여 원본 직접 배정과 구분한다.",
        "",
        "| 옵션 ID | 로컬 교차검증 근거 | 판정 |",
        "|---:|---|---|",
        "| 1045 | `item.dat` 고정효과: 1390 마도풍, 5238 마도풍[Nx], 7145 마도풍[E], 7432 마도풍[R], 7433 마도풍[Nx][R] 모두 장비군 8 | 목걸이 보완 배정 |",
        "| 922 | `item_option_open.dat`의 구조화된 장비 대상 목록에 장비군 8(목걸이) 존재 | 목걸이 보완 배정 |",
        "",
        "추가 교차검증으로 922는 `item.dat`의 1796 `9등급 EX 비늘 장갑` 고정효과 및 개방 옵션의 전용 갑옷 대상에도 존재하고, 1045는 `title.dat`의 `야티카누 요정의 가호`에도 사용된다. 이는 효과의 실제 존재를 뒷받침하지만 비규격 목걸이 보완 판정은 두 ID가 공유하는 장비군 8 연결을 근거로 한다.",
        "",
        "## 로컬 문구로 확인되는 시스템 동작",
        "",
        "| capa ID | 동작 | 확인된 설명 |",
        "|---:|---|---|",
    ]
    for option_id in (1062, 1063, 1064, 1065, 1066, 1067, 1069):
        row = dataset["mechanics_capa"][option_id]
        detail = row["short_text"] or row["description"]
        if row["help_text"]:
            detail += " / " + row["help_text"]
        lines.append(
            f"| {option_id} | {md_escape(row['name'])} | {md_escape(detail)} |"
        )
    lines.extend(
        [
            "",
            "등급 코드는 위 로컬 설명에서 `0=일반`, `1=DX`, `2=ULT`로 직접 확인된다. 로컬 데이터는 ULT 지정 상승 시 무작위 옵션 3개 부여를 명시한다. 운영 구조 참고 자료에서는 일반 0개, DX 1~2개, ULT 3~5개이며 ULT 최대 5칸으로 설명한다. 이 옵션 개수 설명은 외부 운영 참고 근거이고 로컬 DAT 직접 조인과 구분한다: https://sokomin.github.io/information/nonstandard-equipment.html",
            "",
            "### 장비 요구 레벨과 옵션 Tier 구분",
            "",
            "운영 참고 자료는 비규격 베이스 장비를 요구 레벨 1250·1500·1750의 3단계로 구분한다. 이것은 원본 `TierData`의 0~9 그룹과 같은 축이 아니다. 1500 장갑 실물 사례의 물리 공격력 95%, 무기 최대 공격력 17, 물리 강타 대미지 46%, 물리 강타 확률 32%, 공격 속도 34%는 로컬 원본에서 각각 `TierData` 그룹 1·5·4·3·2에서 발견된다. 이는 요구 레벨 1500이 하나의 공통 그룹을 고르지 않는다는 근거지만, 그룹 자체가 게임의 공식 옵션 티어라는 증거는 아니다.",
            "",
            "### Tier와 OptionLevel의 구조",
            "",
            "활성 `OptionLevel`은 전체 옵션에서 공통으로 반복되는 10개 키다: `" + ", ".join(map(str, option_level_keys)) + "`. 69개 일반 정의에서는 원본 `Tier 0..9`와 이 공통 키의 순번이 같지만, 고급 정의는 앞의 세 키를 생략하고 `OptionLevel=27500`을 자체 `Tier=0`으로 저장한다. 따라서 원본 `Tier`는 전 옵션 공통 품질 단계가 아니라 각 옵션 배열 안의 로컬 순번이다. 전 옵션을 같은 축으로 비교할 때는 `OptionLevel` 키 또는 그 정렬 순번을 사용해야 한다.",
            "",
            "로컬 Tier와 공통 OptionLevel 순번이 어긋나는 정의: `" + ", ".join(f"{option['option_id']} {option['name']}" for option in shifted_options) + "`. 이 중 922·1045는 원본 후보표에는 없지만 로컬 교차검증 근거로 목걸이에 보완 배정했다.",
            "",
            "## 장비군별 후보 옵션",
            "",
            "옵션 ID 순서는 원본 `OptionsByItemType` 배열의 순서를 유지하고, 목걸이 행 끝에 보완 옵션 1045·922를 추가했다.",
            "",
            "| 장비군 ID | 장비군 | 후보 수 | 옵션 ID |",
            "|---:|---|---:|---|",
        ]
    )
    for equipment in dataset["equipment"]:
        ids = ", ".join(map(str, equipment["option_ids"]))
        lines.append(
            f"| {equipment['item_group_id']} | {equipment['item_group_name']} | {len(equipment['option_ids'])} | {ids} |"
        )

    lines.extend(
        [
            "",
            "이 배열에 행이 없는 주요 장비군은 장갑 대용(3), 발톱(4), 반지(9), 브로치(12), 팔 문신(13), 어깨 문신(14), 십자가(15), 전용 갑옷(17), 방패(19), 화살(27), 슬링 탄환(31)과 각 직업 보조 무기군(71, 73~79, 81, 83)이다. 이들은 ‘옵션 없음’이 아니라 현재 `InstandardEquip.dat`에 장비별 후보표가 없다는 뜻으로만 해석해야 한다.",
            "",
            "## 옵션 사전",
            "",
            "‘유효 로컬 그룹’은 `OptionLevel != 99999`인 `TierData` 행 수다. 922·1045의 장비 수 1은 원본 직접 연결이 아니라 위 로컬 교차검증에 따른 목걸이 보완 배정이다.",
            "",
            "| ID | 표시문 | 태그 | 장비 수 | 유효 로컬 그룹 | 전체 유효 raw value0 범위 |",
            "|---:|---|---|---:|---:|---:|",
        ]
    )
    for option in dataset["options"]:
        valid = [tier for tier in option["tiers"] if tier["enabled"]]
        values = [vector[0] for tier in valid for vector in tier["roll_values"]]
        lines.append(
            f"| {option['option_id']} | {md_escape(option['short_text'] or option['description'])} | {'/'.join(option['tags'])} | {len(equipment_by_option.get(option['option_id'], []))} | {len(valid)} | {min(values)}~{max(values)} |"
        )

    lines.extend(["", "## 옵션별 정확한 원본 TierData 수치", ""])
    for option in dataset["options"]:
        used_names = equipment_by_option.get(option["option_id"], [])
        status = ", ".join(used_names) if used_names else "현재 후보 장비 없음"
        lines.extend(
            [
                f"### {option['option_id']} · {option['short_text'] or option['description']}",
                "",
                f"- 내부명: `{option['name']}`",
                f"- 태그: `{'/'.join(option['tags'])}`",
                f"- 적용 장비군: {status}",
                "",
                "| 로컬 Tier 인덱스 | OptionLevel 공통 키 | 10개 이산 value0 |",
                "|---:|---:|---|",
            ]
        )
        for tier in option["tiers"]:
            if not tier["enabled"]:
                continue
            values = [vector[0] for vector in tier["roll_values"]]
            lines.append(
                f"| {tier['tier']} | {tier['option_level_raw']} | {compact_rolls(values)} |"
            )
        disabled = [tier["tier"] for tier in option["tiers"] if not tier["enabled"]]
        if disabled:
            lines.extend(
                [
                    "",
                    f"비활성 센티널 로컬 인덱스: `{', '.join(map(str, disabled))}` (`OptionLevel=99999`, 렌더링 제외)",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "## 접두 문구",
            "",
            "원본에는 60개 `PrefixTagName`이 배열 순서로 존재하지만 어떤 산식으로 옵션 티어/아이템 등급과 연결되는지는 이 파일에 없다. 따라서 번호와 원문만 보존한다.",
            "",
            "| 인덱스 | 문구 | 인덱스 | 문구 | 인덱스 | 문구 |",
            "|---:|---|---:|---|---:|---|",
        ]
    )
    prefixes = dataset["prefix_tag_names"]
    for start in range(0, 20):
        cells = []
        for index in (start, start + 20, start + 40):
            cells.extend((str(index), prefixes[index]))
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## 재료·분해 레코드",
            "",
            "`MaterialData`와 `DisJointData`도 같은 원본에 있다. 로컬 아이템 ID-명칭 직접 조인은 아직 없지만, 외부 운영 자료의 8개 재료 순서·금괴 비용·동작이 원본 ID 14186~14193의 비용 1/2/2/3/3/3/5/5와 정확히 일치한다. 아래 외부 대응은 로컬 직접 명칭이 아니라 운영 자료 교차검증 결과다.",
            "",
            "| Item ID | 외부 운영 대응 | 금괴 | 용도 |",
            "|---:|---|---:|---|",
            "| 14186 | 페이즈 튜너 | 1 | 미감정 장비 감정 |",
            "| 14187 | 파워 노드 | 2 | 일반→DX, 옵션 1개 추가 |",
            "| 14188 | 마이티 노드 | 2 | DX→ULT, 옵션 1개 추가 |",
            "| 14189 | 캐퍼시티 노드 | 3 | DX 옵션 칸 추가 |",
            "| 14190 | 디스클로저 노드 | 3 | ULT 옵션 칸 추가 |",
            "| 14191 | 엑셀 노드 | 3 | ULT 상승과 무작위 옵션 3개 |",
            "| 14192 | 인버터 노드 | 5 | 옵션 종류 재설정 |",
            "| 14193 | 에니그마틱 노드 | 5 | 옵션 수치 재설정 |",
            "| 14195 | 아모르퍼스 더스트 | - | 분해 보상 및 상자 교환 재화 |",
            "",
            "### MaterialData",
            "",
            "| MaterialIdx | MaterialItemCount | GoldBarCost |",
            "|---:|---:|---:|",
        ]
    )
    for row in dataset["material_data"]:
        lines.append(
            f"| {row['MaterialIdx']} | {row['MaterialItemCount']} | {row['GoldBarCost']} |"
        )
    lines.extend(
        [
            "",
            "### DisJointData",
            "",
            "| Grade | DisjointCondition | ItemCountRange | ItemIndex |",
            "|---:|---:|---|---:|",
        ]
    )
    for condition, reward in dataset["disjoint_data"]:
        lines.append(
            f"| {condition['Grade']} | {condition['DisjointCondition']} | {reward['ItemCountRange'][0]}~{reward['ItemCountRange'][1]} | {reward['ItemIndex']} |"
        )

    lines.extend(
        [
            "",
            "## 렌더링 제안",
            "",
            "통합 장비 옵션 탐색기의 비규격 탭은 렌더링 직전 CSV를 입력으로 사용한다.",
            "",
            "- 상단 필터: 장비군, 태그, 옵션명 검색, `OptionLevel` 공통 수치 구간 0~9",
            "- 전체 결과: 옵션당 한 행과 전체 유효 범위·후보 수",
            "- 구간 결과: 공통 수치 구간, `OptionLevel` 원시값, 정확한 후보 수치 10개",
            "- 상세 패널: 로컬 Tier 인덱스, 공통 구간, 오프셋, 각 구간의 원시 벡터",
            "- 아이템 카드 미리보기: 일반 0줄, DX 1~2줄, ULT 3~5줄. 원본 `TierData` 숫자는 해석 확정 전까지 ‘원본 수치 그룹’으로 표시한다.",
            "- 비활성 센티널은 기본적으로 숨기고 개발자 모드에서만 회색으로 노출한다.",
            "",
            "CSV는 표/차트 입력에 적합하고 JSON은 브라우저 필터와 아이템 카드 렌더링에 적합하다. 브라우저에서 로컬 파일 접근 문제를 피하려면 최종 HTML 생성 시 JSON을 `<script type=\"application/json\">`에 내장하는 방식을 권장한다.",
            "",
            "## 아직 확정하지 않은 것",
            "",
            "- `OptionLevel`이 요구 레벨, 내부 가중치, 종합 옵션 레벨 중 무엇인지",
            "- 60개 접두 문구와 Tier/등급의 연결 산식",
            "- `DisjointCondition 0=감정/1=미감정` 및 재료 ID 대응의 로컬 아이템 명칭 직접 조인(현재는 외부 운영 자료와 수치 교차검증)",
            "- 원본 비규격 후보표에서 922·1045의 목걸이 행 직접 배정이 누락된 이유",
            "",
        ]
    )
    return "\n".join(lines)


def run_pipeline(
    *,
    data_dir: Path,
    markdown_path: Path,
    json_path: Path,
    csv_path: Path,
    render_csv_path: Path,
) -> dict[str, Any]:
    dataset = build_dataset(data_dir)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(csv_path, dataset)
    render_row_count = write_render_csv(render_csv_path, dataset)
    markdown_path.write_text(markdown(dataset), encoding="utf-8")
    return {**dataset["summary"], "render_row_count": render_row_count}
