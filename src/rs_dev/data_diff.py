"""File- and record-level comparison for two game Data-directory snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable


def parse_capa(path: Path) -> dict[int, dict[str, Any]]:
    """Load the capa parser only when a changed capa.dat needs details."""
    from rs_dev.parsers.capa import parse_capa as parser

    return parser(path)


def parse_item_groups(path: Path) -> dict[int, str]:
    """Load the item-group parser only when it is needed."""
    from rs_dev.parsers.item_groups import parse_item_groups as parser

    return parser(path)


def parse_item_option_open(path: Path) -> list[Any]:
    """Load the open-option parser only when it is needed."""
    from rs_dev.parsers.item_option_open import parse_item_option_open as parser

    return parser(path)


def parse_instandard_equip(path: Path) -> Any:
    """Load the InstandardEquip parser only when it is needed."""
    from rs_dev.parsers.instandard_equip import parse_instandard_equip as parser

    return parser(path)


def parse_japanese_llt(path: Path) -> list[Any]:
    """Load the japanese.llt parser only when it is needed."""
    from rs_dev.parsers.japanese_llt import parse_japanese_llt as parser

    return parser(path)


@dataclass(frozen=True)
class FileChange:
    relative_path: Path
    status: str
    before_size: int | None = None
    after_size: int | None = None


@dataclass(frozen=True)
class RecordChange:
    status: str
    record_id: str
    fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecordDiff:
    relative_path: Path
    before_count: int
    after_count: int
    changes: tuple[RecordChange, ...]
    collection_counts: tuple[tuple[str, int, int], ...] = ()


@dataclass
class ComparisonReport:
    changes: list[FileChange] = field(default_factory=list)
    unchanged_count: int = 0
    warnings: list[str] = field(default_factory=list)
    record_diffs: list[RecordDiff] = field(default_factory=list)


def _is_target(path: Path) -> bool:
    return path.suffix.lower() == ".dat" or path.name.lower() == "japanese.llt"


def _target_files(root: Path) -> dict[Path, Path]:
    return {
        path.relative_to(root): path
        for path in root.rglob("*")
        if path.is_file() and _is_target(path)
    }


def _fingerprint(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha256(data).hexdigest()


def _read_file(path: Path, report: ComparisonReport) -> tuple[int, str] | None:
    try:
        return _fingerprint(path)
    except OSError as error:
        report.warnings.append(f"파일을 읽을 수 없습니다: {path} ({error})")
        return None


def _mapping_record_changes(
    before: dict[int, Any],
    after: dict[int, Any],
    fields_for_change: Callable[[Any, Any], tuple[str, ...]],
) -> tuple[RecordChange, ...]:
    changes: list[RecordChange] = []
    for record_id in sorted(before.keys() | after.keys()):
        if record_id not in before:
            changes.append(RecordChange("추가", str(record_id)))
        elif record_id not in after:
            changes.append(RecordChange("삭제", str(record_id)))
        else:
            fields = fields_for_change(before[record_id], after[record_id])
            if fields:
                changes.append(RecordChange("수정", str(record_id), fields))
    return tuple(changes)


def _unique_mapping(
    records: Any,
    key_for_record: Callable[[Any], Any],
    value_for_record: Callable[[Any], Any],
    collection_name: str,
) -> dict[Any, Any]:
    """Build a record mapping while rejecting ambiguous duplicate keys."""
    result: dict[Any, Any] = {}
    for record in records:
        key = key_for_record(record)
        if key in result:
            raise ValueError(f"중복 레코드 키: {collection_name}:{key}")
        result[key] = value_for_record(record)
    return result


def _capa_diff(relative_path: Path, before_path: Path, after_path: Path) -> RecordDiff:
    before = parse_capa(before_path)
    after = parse_capa(after_path)
    comparison_fields = ("name", "description", "short_text", "help_text")
    return RecordDiff(
        relative_path,
        len(before),
        len(after),
        _mapping_record_changes(
            before,
            after,
            lambda old, new: tuple(
                name for name in comparison_fields if old[name] != new[name]
            ),
        ),
    )


def _item_groups_diff(
    relative_path: Path, before_path: Path, after_path: Path
) -> RecordDiff:
    before = parse_item_groups(before_path)
    after = parse_item_groups(after_path)
    return RecordDiff(
        relative_path,
        len(before),
        len(after),
        _mapping_record_changes(
            before,
            after,
            lambda old, new: ("name",) if old != new else (),
        ),
    )


def _item_option_open_diff(
    relative_path: Path, before_path: Path, after_path: Path
) -> RecordDiff:
    before_blocks = {
        block.block_index: block for block in parse_item_option_open(before_path)
    }
    after_blocks = {
        block.block_index: block for block in parse_item_option_open(after_path)
    }
    block_fields = ("section_type", "section_group", "group_ids")
    row_fields = (
        "candidate_index",
        "option_id",
        "packed_value",
        "float_a",
        "float_b",
        "tier",
    )

    def changed_fields(old: Any, new: Any) -> tuple[str, ...]:
        fields = [
            name for name in block_fields if getattr(old, name) != getattr(new, name)
        ]
        before_rows = {row.row_index: row for row in old.rows}
        after_rows = {row.row_index: row for row in new.rows}
        for row_index in sorted(before_rows.keys() | after_rows.keys()):
            old_row = before_rows.get(row_index)
            new_row = after_rows.get(row_index)
            if old_row is None or new_row is None:
                fields.append(f"rows[{row_index}]")
                continue
            fields.extend(
                f"rows[{row_index}].{name}"
                for name in row_fields
                if getattr(old_row, name) != getattr(new_row, name)
            )
        return tuple(fields)

    changes = tuple(
        RecordChange(change.status, f"block:{change.record_id}", change.fields)
        for change in _mapping_record_changes(before_blocks, after_blocks, changed_fields)
    )
    before_row_count = sum(len(block.rows) for block in before_blocks.values())
    after_row_count = sum(len(block.rows) for block in after_blocks.values())
    return RecordDiff(
        relative_path,
        len(before_blocks),
        len(after_blocks),
        changes,
        (("행", before_row_count, after_row_count),),
    )


def _instandard_option_fields(old: Any, new: Any) -> tuple[str, ...]:
    fields: list[str] = []
    if old.TagName != new.TagName:
        fields.append("TagName")

    before_tiers = _unique_mapping(
        old.TierData, lambda tier: tier.Tier, lambda tier: tier, "OptionData.TierData"
    )
    after_tiers = _unique_mapping(
        new.TierData, lambda tier: tier.Tier, lambda tier: tier, "OptionData.TierData"
    )
    for tier_id in sorted(before_tiers.keys() | after_tiers.keys()):
        old_tier = before_tiers.get(tier_id)
        new_tier = after_tiers.get(tier_id)
        prefix = f"TierData[{tier_id}]"
        if old_tier is None or new_tier is None:
            fields.append(prefix)
            continue
        if old_tier.OptionLevel != new_tier.OptionLevel:
            fields.append(f"{prefix}.OptionLevel")
        for roll_index, (old_roll, new_roll) in enumerate(
            zip(old_tier.TierValue, new_tier.TierValue)
        ):
            fields.extend(
                f"{prefix}.TierValue[{roll_index}][{component_index}]"
                for component_index, (old_value, new_value) in enumerate(
                    zip(old_roll, new_roll)
                )
                if old_value != new_value
            )
    return tuple(fields)


def _nested_fields(old: Any, new: Any, prefix: str) -> tuple[str, ...]:
    """Return stable field paths for a changed value without printing values."""
    if isinstance(old, dict) and isinstance(new, dict):
        fields: list[str] = []
        for key in sorted(old.keys() | new.keys(), key=str):
            key_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in old or key not in new:
                fields.append(key_prefix)
            else:
                fields.extend(_nested_fields(old[key], new[key], key_prefix))
        return tuple(fields)
    if isinstance(old, (list, tuple)) and isinstance(new, (list, tuple)):
        fields = []
        for index in range(max(len(old), len(new))):
            index_prefix = f"{prefix}[{index}]"
            if index >= len(old) or index >= len(new):
                fields.append(index_prefix)
            else:
                fields.extend(_nested_fields(old[index], new[index], index_prefix))
        return tuple(fields)
    return (prefix,) if old != new else ()


def _instandard_disjoint_fields(old: Any, new: Any) -> tuple[str, ...]:
    contract_fields = (
        "DisjointCondition",
        "Grade",
        "ItemCountRange",
        "ItemIndex",
    )
    return tuple(
        field
        for field in _nested_fields(old, new, "")
        if any(
            field == name
            or field.startswith(f"{name}[")
            or field.endswith(f".{name}")
            or f".{name}[" in field
            for name in contract_fields
        )
    )


def _instandard_equip_diff(
    relative_path: Path, before_path: Path, after_path: Path
) -> RecordDiff:
    before = parse_instandard_equip(before_path)
    after = parse_instandard_equip(after_path)
    collection_counts = (
        ("OptionData", len(before.OptionData), len(after.OptionData)),
        ("OptionsByItemType", len(before.OptionsByItemType), len(after.OptionsByItemType)),
        ("MaterialData", len(before.MaterialData), len(after.MaterialData)),
        ("PrefixTagName", len(before.PrefixTagName), len(after.PrefixTagName)),
        ("DisJointData", len(before.DisJointData), len(after.DisJointData)),
    )
    for options in (before.OptionData, after.OptionData):
        for option in options:
            _unique_mapping(
                option.TierData,
                lambda tier: tier.Tier,
                lambda tier: tier,
                "OptionData.TierData",
            )
    changes: list[RecordChange] = []

    def add_collection(
        name: str, before_records: dict[int, Any], after_records: dict[int, Any],
        fields_for_change: Callable[[Any, Any], tuple[str, ...]],
    ) -> None:
        changes.extend(
            RecordChange(change.status, f"{name}:{change.record_id}", change.fields)
            for change in _mapping_record_changes(
                before_records, after_records, fields_for_change
            )
        )

    add_collection(
        "OptionData",
        _unique_mapping(
            before.OptionData,
            lambda option: option.OptionCapaIndex,
            lambda option: option,
            "OptionData",
        ),
        _unique_mapping(
            after.OptionData,
            lambda option: option.OptionCapaIndex,
            lambda option: option,
            "OptionData",
        ),
        _instandard_option_fields,
    )

    def option_ids_fields(old: list[int], new: list[int]) -> tuple[str, ...]:
        fields = [f"option_ids (-{value})" for value in sorted(set(old) - set(new))]
        fields.extend(f"option_ids (+{value})" for value in sorted(set(new) - set(old)))
        return tuple(fields) if fields else (("option_ids",) if old != new else ())

    add_collection(
        "OptionsByItemType",
        _unique_mapping(
            before.OptionsByItemType,
            lambda record: record[0],
            lambda record: record[1],
            "OptionsByItemType",
        ),
        _unique_mapping(
            after.OptionsByItemType,
            lambda record: record[0],
            lambda record: record[1],
            "OptionsByItemType",
        ),
        option_ids_fields,
    )
    add_collection(
        "MaterialData",
        _unique_mapping(
            before.MaterialData,
            lambda record: record["MaterialIdx"],
            lambda record: record,
            "MaterialData",
        ),
        _unique_mapping(
            after.MaterialData,
            lambda record: record["MaterialIdx"],
            lambda record: record,
            "MaterialData",
        ),
        lambda old, new: tuple(
            str(field)
            for field in sorted(old.keys() | new.keys(), key=str)
            if field not in old or field not in new or old[field] != new[field]
        ),
    )
    add_collection(
        "PrefixTagName",
        dict(enumerate(before.PrefixTagName)),
        dict(enumerate(after.PrefixTagName)),
        lambda old, new: ("text",) if old != new else (),
    )
    add_collection(
        "DisJointData",
        dict(enumerate(before.DisJointData)),
        dict(enumerate(after.DisJointData)),
        _instandard_disjoint_fields,
    )
    return RecordDiff(
        relative_path,
        sum(before_count for _name, before_count, _after_count in collection_counts),
        sum(after_count for _name, _before_count, after_count in collection_counts),
        tuple(changes),
        collection_counts,
    )


def _japanese_llt_diff(
    relative_path: Path, before_path: Path, after_path: Path
) -> RecordDiff:
    before_records = parse_japanese_llt(before_path)
    after_records = parse_japanese_llt(after_path)

    def record_key(record: Any) -> tuple[int, int, int | None, int | None]:
        return (
            record.section_id,
            record.text_id,
            record.variant_id,
            record.sub_variant_id,
        )

    def record_id(key: tuple[int, int, int | None, int | None]) -> str:
        return "/".join(str(value) for value in key)

    before = _unique_mapping(
        before_records, record_key, lambda record: record, "japanese.llt"
    )
    after = _unique_mapping(
        after_records, record_key, lambda record: record, "japanese.llt"
    )
    changes: list[RecordChange] = []
    for key in sorted(before.keys() | after.keys(), key=record_id):
        if key not in before:
            changes.append(RecordChange("추가", record_id(key)))
        elif key not in after:
            changes.append(RecordChange("삭제", record_id(key)))
        else:
            fields = tuple(
                name
                for name in ("text", "kind")
                if getattr(before[key], name) != getattr(after[key], name)
            )
            if fields:
                changes.append(RecordChange("수정", record_id(key), fields))
    return RecordDiff(relative_path, len(before_records), len(after_records), tuple(changes))


_RECORD_DIFFERS: dict[str, Callable[[Path, Path, Path], RecordDiff]] = {
    "capa.dat": _capa_diff,
    "simplegametext.dat": _item_groups_diff,
    "item_option_open.dat": _item_option_open_diff,
    "instandardequip.dat": _instandard_equip_diff,
    "japanese.llt": _japanese_llt_diff,
}


def _add_record_diff(
    relative_path: Path, before_path: Path, after_path: Path, report: ComparisonReport
) -> None:
    differ = _RECORD_DIFFERS.get(relative_path.name.lower())
    if differ is None:
        return
    try:
        report.record_diffs.append(differ(relative_path, before_path, after_path))
    except Exception as error:
        report.warnings.append(f"파일을 파싱할 수 없습니다: {relative_path} ({error})")


def compare_directories(before_root: Path, after_root: Path) -> ComparisonReport:
    """Compare target files and collect read errors without stopping the scan."""
    report = ComparisonReport()
    invalid_roots = [root for root in (before_root, after_root) if not root.is_dir()]
    if invalid_roots:
        report.warnings.extend(
            f"스냅샷 경로가 디렉터리가 아닙니다: {root}" for root in invalid_roots
        )
        return report

    before_files = _target_files(before_root)
    after_files = _target_files(after_root)

    for relative_path in sorted(before_files.keys() | after_files.keys()):
        before = before_files.get(relative_path)
        after = after_files.get(relative_path)
        if before is None:
            after_data = _read_file(after, report)
            report.changes.append(
                FileChange(
                    relative_path,
                    "추가",
                    after_size=after_data[0] if after_data is not None else None,
                )
            )
            continue
        if after is None:
            before_data = _read_file(before, report)
            report.changes.append(
                FileChange(
                    relative_path,
                    "삭제",
                    before_size=before_data[0] if before_data is not None else None,
                )
            )
            continue

        before_data = _read_file(before, report)
        after_data = _read_file(after, report)
        if before_data is None or after_data is None:
            continue
        if before_data[1] == after_data[1]:
            report.unchanged_count += 1
            continue
        report.changes.append(
            FileChange(relative_path, "수정", before_data[0], after_data[0])
        )
        _add_record_diff(relative_path, before, after, report)
    return report


def render_report(report: ComparisonReport) -> str:
    """Render the concise Korean terminal report for file-level findings."""
    counts = {
        status: sum(change.status == status for change in report.changes)
        for status in ("추가", "삭제", "수정")
    }
    lines = [
        "Data 비교 보고서",
        f"파일: 추가 {counts['추가']}, 삭제 {counts['삭제']}, 수정 {counts['수정']}, 동일 {report.unchanged_count}",
    ]
    if report.changes:
        lines.append("")
    for change in report.changes:
        size = (
            f" ({change.before_size} B → {change.after_size} B)"
            if change.status == "수정"
            else ""
        )
        lines.append(f"[{change.status}] {change.relative_path}{size}")
        record_diff = next(
            (
                diff
                for diff in report.record_diffs
                if diff.relative_path == change.relative_path
            ),
            None,
        )
        if record_diff is None:
            continue
        counts = {
            status: sum(
                record_change.status == status for record_change in record_diff.changes
            )
            for status in ("추가", "삭제", "수정")
        }
        lines.extend(
            (
                f"  레코드: {record_diff.before_count} → {record_diff.after_count}",
                f"  추가 {counts['추가']}, 삭제 {counts['삭제']}, 수정 {counts['수정']}",
            )
        )
        lines.extend(
            f"  {name}: {before_count} → {after_count}"
            for name, before_count, after_count in record_diff.collection_counts
        )
        for record_change in record_diff.changes[:10]:
            detail = (
                f": {', '.join(record_change.fields)}"
                if record_change.status == "수정"
                else ""
            )
            lines.append(f"  - {record_change.status} {record_change.record_id}{detail}")
        remaining = len(record_diff.changes) - 10
        if remaining > 0:
            lines.append(f"  - 상세 변경 외 {remaining}건")
    if report.warnings:
        lines.extend(("", f"경고: {len(report.warnings)}개"))
        lines.extend(f"- {warning}" for warning in report.warnings)
    return "\n".join(lines)
