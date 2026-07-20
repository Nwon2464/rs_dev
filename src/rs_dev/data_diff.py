"""게임 업데이트 전후의 한국어 웹 관련 데이터를 비교한다."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable


DETAIL_FILE_NAMES = {
    "capa.dat",
    "simplegametext.dat",
    "item_option_open.dat",
    "instandardequip.dat",
}
JAPANESE_FILE_NAME = "japanese.llt"
REQUIRED_FILES = (
    Path("capa.dat"),
    Path("item_option_open.dat"),
    Path("InstandardEquip.dat"),
    Path("simpleGameText.dat"),
    Path("language/japanese.llt"),
)

LIMITATIONS = [
    "현재 한국어 웹에서 사용하는 필드만 상세 비교합니다.",
    "capa.dat의 help_text는 현재 웹에서 사용하지 않아 상세 비교하지 않습니다.",
    "InstandardEquip.dat의 MaterialData, PrefixTagName, DisJointData는 상세 비교하지 않습니다.",
    "japanese.llt는 전체 파일 해시로 변경 여부만 확인합니다.",
    "바이트 비교는 파서가 해석한 영역과 해석하지 않은 영역을 구분하지 않습니다.",
    "불일치 바이트 수는 동일 offset끼리 비교하므로 중간 삽입·삭제 시 실제 변경량보다 크게 계산될 수 있습니다.",
    "자동 검사 결과는 완전한 웹 반영 판정이 아닙니다.",
]


def parse_capa(path: Path) -> dict[int, dict[str, Any]]:
    from rs_dev.parsers.capa import parse_capa as parser

    return parser(path)


def parse_item_groups(path: Path) -> dict[int, str]:
    from rs_dev.parsers.item_groups import parse_item_groups as parser

    return parser(path)


def parse_item_option_open(path: Path) -> list[Any]:
    from rs_dev.parsers.item_option_open import parse_item_option_open as parser

    return parser(path)


def parse_instandard_equip(path: Path) -> Any:
    from rs_dev.parsers.instandard_equip import parse_instandard_equip as parser

    return parser(path)


@dataclass(frozen=True)
class ByteDiff:
    offset_mismatch_bytes: int
    changed_regions: int
    first_change_offset: int | None


@dataclass(frozen=True)
class FileChange:
    relative_path: Path
    status: str
    before_size: int | None = None
    after_size: int | None = None
    before_sha256: str | None = None
    after_sha256: str | None = None
    byte_diff: ByteDiff | None = None


@dataclass(frozen=True)
class ValueChange:
    field_path: str
    before: Any
    after: Any


@dataclass(frozen=True)
class RecordChange:
    status: str
    record_id: str
    fields: tuple[str, ...] = ()
    values: tuple[ValueChange, ...] = ()
    korean_name: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class RecordDiff:
    relative_path: Path
    before_count: int
    after_count: int
    changes: tuple[RecordChange, ...]
    collection_counts: tuple[tuple[str, int, int], ...] = ()
    understood_scope: str = ""
    uninspected_scope: str = ""


@dataclass
class ComparisonReport:
    changes: list[FileChange] = field(default_factory=list)
    file_results: list[FileChange] = field(default_factory=list)
    unchanged_count: int = 0
    warnings: list[str] = field(default_factory=list)
    record_diffs: list[RecordDiff] = field(default_factory=list)
    inspected_paths: list[Path] = field(default_factory=list)
    parse_failures: set[Path] = field(default_factory=set)
    recommended_codex_checks: list[str] = field(default_factory=list)
    fatal_error: bool = False

    @property
    def status(self) -> str:
        if self.fatal_error:
            return "검사 중단"
        return "검사 불완전" if self.warnings else "검사 완료"


def _is_target(path: Path) -> bool:
    return path.suffix.lower() == ".dat" or path.name.lower() == JAPANESE_FILE_NAME


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


def _preflight_required_files(
    before_root: Path, after_root: Path, report: ComparisonReport
) -> bool:
    """필수 입력을 모두 읽고 파싱한다. 첫 실패에서 검사를 중단한다."""
    for root in (before_root, after_root):
        for relative_path in REQUIRED_FILES:
            path = root / relative_path
            if not path.is_file():
                report.warnings.append(f"필수 파일이 없습니다: {path}")
                report.fatal_error = True
                return False
            try:
                _fingerprint(path)
            except OSError as error:
                report.warnings.append(f"필수 파일을 읽을 수 없습니다: {path} ({error})")
                report.fatal_error = True
                return False

    parsers: tuple[tuple[Path, Callable[[Path], Any]], ...] = (
        (Path("capa.dat"), parse_capa),
        (Path("simpleGameText.dat"), parse_item_groups),
        (Path("item_option_open.dat"), parse_item_option_open),
        (Path("InstandardEquip.dat"), parse_instandard_equip),
    )
    for relative_path, parser in parsers:
        for root in (before_root, after_root):
            path = root / relative_path
            try:
                parser(path)
            except Exception as error:
                report.warnings.append(f"필수 파일을 파싱할 수 없습니다: {path} ({error})")
                report.fatal_error = True
                return False
    return True


def _byte_diff(before_path: Path, after_path: Path) -> ByteDiff:
    before = before_path.read_bytes()
    after = after_path.read_bytes()
    limit = max(len(before), len(after))
    changed = 0
    regions = 0
    first: int | None = None
    in_region = False
    for offset in range(limit):
        different = (
            offset >= len(before)
            or offset >= len(after)
            or before[offset] != after[offset]
        )
        if different:
            changed += 1
            if not in_region:
                regions += 1
                if first is None:
                    first = offset
            in_region = True
        else:
            in_region = False
    return ByteDiff(changed, regions, first)


def _plain(value: Any) -> Any:
    """Pydantic 모델과 튜플을 JSON에 안전한 값으로 바꾼다."""
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, SimpleNamespace):
        return _plain(vars(value))
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _whole_record_change(
    status: str,
    record_id: str,
    before: Any,
    after: Any,
    *,
    korean_name: str | None = None,
    summary: str | None = None,
) -> RecordChange:
    return RecordChange(
        status,
        record_id,
        (),
        (ValueChange("$", _plain(before), _plain(after)),),
        korean_name,
        summary,
    )


def _mapping_record_changes(
    before: dict[Any, Any],
    after: dict[Any, Any],
    values_for_change: Callable[[Any, Any], tuple[ValueChange, ...]],
    *,
    id_prefix: str = "",
    name_for_record: Callable[[Any], str | None] | None = None,
    summary_for_change: Callable[[str, Any, Any, tuple[ValueChange, ...]], str] | None = None,
) -> tuple[RecordChange, ...]:
    changes: list[RecordChange] = []
    for key in sorted(before.keys() | after.keys()):
        record_id = f"{id_prefix}{key}"
        old = before.get(key)
        new = after.get(key)
        record_for_name = new if key in after else old
        korean_name = name_for_record(record_for_name) if name_for_record else None
        if key not in before:
            changes.append(
                _whole_record_change(
                    "추가", record_id, None, new, korean_name=korean_name,
                    summary=f"{record_id} 레코드가 추가되었습니다.",
                )
            )
        elif key not in after:
            changes.append(
                _whole_record_change(
                    "삭제", record_id, old, None, korean_name=korean_name,
                    summary=f"{record_id} 레코드가 삭제되었습니다.",
                )
            )
        else:
            values = values_for_change(old, new)
            if values:
                summary = (
                    summary_for_change(record_id, old, new, values)
                    if summary_for_change
                    else f"{record_id} 레코드의 웹 관련 필드 {len(values)}개가 변경되었습니다."
                )
                changes.append(
                    RecordChange(
                        "수정",
                        record_id,
                        tuple(value.field_path for value in values),
                        values,
                        korean_name,
                        summary,
                    )
                )
    return tuple(changes)


def _field_values(old: Any, new: Any, fields: tuple[str, ...]) -> tuple[ValueChange, ...]:
    return tuple(
        ValueChange(name, _plain(old[name]), _plain(new[name]))
        for name in fields
        if old[name] != new[name]
    )


def _capa_diff(relative_path: Path, before_path: Path, after_path: Path) -> RecordDiff:
    fields = ("name", "description", "short_text")
    before = {
        record_id: {name: record[name] for name in fields}
        for record_id, record in parse_capa(before_path).items()
    }
    after = {
        record_id: {name: record[name] for name in fields}
        for record_id, record in parse_capa(after_path).items()
    }

    def summary(record_id: str, old: Any, new: Any, values: tuple[ValueChange, ...]) -> str:
        if len(values) == 1:
            value = values[0]
            return f"옵션 ID {record_id}의 {value.field_path}이(가) {value.before!r}에서 {value.after!r}(으)로 변경되었습니다."
        return f"옵션 ID {record_id}의 한국어 웹 문구 {len(values)}개가 변경되었습니다."

    return RecordDiff(
        relative_path,
        len(before),
        len(after),
        _mapping_record_changes(
            before,
            after,
            lambda old, new: _field_values(old, new, fields),
            name_for_record=lambda record: record.get("name"),
            summary_for_change=summary,
        ),
        understood_scope="한국어 옵션 이름, 설명, 짧은 문구",
        uninspected_scope="help_text와 파서가 해석하지 않는 바이트 영역",
    )


def _item_groups_diff(relative_path: Path, before_path: Path, after_path: Path) -> RecordDiff:
    before = parse_item_groups(before_path)
    after = parse_item_groups(after_path)
    return RecordDiff(
        relative_path,
        len(before),
        len(after),
        _mapping_record_changes(
            before,
            after,
            lambda old, new: (ValueChange("name", old, new),) if old != new else (),
            name_for_record=lambda name: name,
            summary_for_change=lambda record_id, old, new, values: (
                f"장비 그룹 ID {record_id}의 한국어 이름이 {old!r}에서 {new!r}(으)로 변경되었습니다."
            ),
        ),
        understood_scope="한국어 장비 그룹 ID와 이름",
        uninspected_scope="장비 그룹 사전 밖의 데이터와 파서가 해석하지 않는 바이트 영역",
    )


def _unique_mapping(
    records: Any,
    key_for_record: Callable[[Any], Any],
    value_for_record: Callable[[Any], Any],
    collection_name: str,
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for record in records:
        key = key_for_record(record)
        if key in result:
            raise ValueError(f"중복 레코드 키: {collection_name}:{key}")
        result[key] = value_for_record(record)
    return result


def _item_option_open_diff(relative_path: Path, before_path: Path, after_path: Path) -> RecordDiff:
    before_blocks = _unique_mapping(
        parse_item_option_open(before_path), lambda block: block.block_index, lambda block: block, "block"
    )
    after_blocks = _unique_mapping(
        parse_item_option_open(after_path), lambda block: block.block_index, lambda block: block, "block"
    )
    block_fields = ("section_type", "section_group", "group_ids")
    row_fields = ("candidate_index", "option_id", "packed_value", "float_a", "float_b", "tier")

    def changed_values(old: Any, new: Any) -> tuple[ValueChange, ...]:
        values = [
            ValueChange(name, _plain(getattr(old, name)), _plain(getattr(new, name)))
            for name in block_fields
            if getattr(old, name) != getattr(new, name)
        ]
        before_rows = _unique_mapping(old.rows, lambda row: row.row_index, lambda row: row, "rows")
        after_rows = _unique_mapping(new.rows, lambda row: row.row_index, lambda row: row, "rows")
        for row_index in sorted(before_rows.keys() | after_rows.keys()):
            old_row = before_rows.get(row_index)
            new_row = after_rows.get(row_index)
            path = f"rows[{row_index}]"
            if old_row is None or new_row is None:
                values.append(ValueChange(path, _plain(old_row), _plain(new_row)))
                continue
            values.extend(
                ValueChange(
                    f"{path}.{name}",
                    _plain(getattr(old_row, name)),
                    _plain(getattr(new_row, name)),
                )
                for name in row_fields
                if getattr(old_row, name) != getattr(new_row, name)
            )
        return tuple(values)

    def summary(record_id: str, old: Any, new: Any, values: tuple[ValueChange, ...]) -> str:
        if len(values) == 1 and values[0].field_path.startswith("rows["):
            value = values[0]
            row_path, _, field_name = value.field_path.partition("].")
            if field_name:
                row_index = row_path.removeprefix("rows[")
                block_index = record_id.removeprefix("block:")
                return f"블록 {block_index}의 {row_index}번 행에서 {field_name}이(가) {value.before!r}에서 {value.after!r}(으)로 변경되었습니다."
        return f"{record_id}의 웹 관련 필드 {len(values)}개가 변경되었습니다."

    changes = _mapping_record_changes(
        before_blocks,
        after_blocks,
        changed_values,
        id_prefix="block:",
        summary_for_change=summary,
    )
    before_rows = sum(len(block.rows) for block in before_blocks.values())
    after_rows = sum(len(block.rows) for block in after_blocks.values())
    return RecordDiff(
        relative_path,
        len(before_blocks),
        len(after_blocks),
        changes,
        (("행", before_rows, after_rows),),
        "일반 개방 옵션 블록, 장비 그룹, 옵션 ID, 수치, 티어",
        "파서가 해석하지 않는 바이트 영역",
    )


def _instandard_option_values(old: Any, new: Any) -> tuple[ValueChange, ...]:
    values: list[ValueChange] = []
    if old.TagName != new.TagName:
        values.append(ValueChange("TagName", _plain(old.TagName), _plain(new.TagName)))
    before_tiers = _unique_mapping(old.TierData, lambda tier: tier.Tier, lambda tier: tier, "OptionData.TierData")
    after_tiers = _unique_mapping(new.TierData, lambda tier: tier.Tier, lambda tier: tier, "OptionData.TierData")
    for tier_id in sorted(before_tiers.keys() | after_tiers.keys()):
        old_tier = before_tiers.get(tier_id)
        new_tier = after_tiers.get(tier_id)
        prefix = f"TierData[{tier_id}]"
        if old_tier is None or new_tier is None:
            values.append(ValueChange(prefix, _plain(old_tier), _plain(new_tier)))
            continue
        if old_tier.OptionLevel != new_tier.OptionLevel:
            values.append(ValueChange(f"{prefix}.OptionLevel", old_tier.OptionLevel, new_tier.OptionLevel))
        max_rolls = max(len(old_tier.TierValue), len(new_tier.TierValue))
        for roll_index in range(max_rolls):
            old_roll = old_tier.TierValue[roll_index] if roll_index < len(old_tier.TierValue) else None
            new_roll = new_tier.TierValue[roll_index] if roll_index < len(new_tier.TierValue) else None
            if old_roll is None or new_roll is None:
                values.append(ValueChange(f"{prefix}.TierValue[{roll_index}]", _plain(old_roll), _plain(new_roll)))
                continue
            for component_index in range(max(len(old_roll), len(new_roll))):
                old_value = old_roll[component_index] if component_index < len(old_roll) else None
                new_value = new_roll[component_index] if component_index < len(new_roll) else None
                if old_value != new_value:
                    values.append(ValueChange(f"{prefix}.TierValue[{roll_index}][{component_index}]", old_value, new_value))
    return tuple(values)


def _instandard_equip_diff(relative_path: Path, before_path: Path, after_path: Path) -> RecordDiff:
    before = parse_instandard_equip(before_path)
    after = parse_instandard_equip(after_path)

    # 추가/삭제된 옵션 안의 중복 티어도 검사한다.
    for options in (before.OptionData, after.OptionData):
        for option in options:
            _unique_mapping(option.TierData, lambda tier: tier.Tier, lambda tier: tier, "OptionData.TierData")

    before_options = _unique_mapping(before.OptionData, lambda option: option.OptionCapaIndex, lambda option: option, "OptionData")
    after_options = _unique_mapping(after.OptionData, lambda option: option.OptionCapaIndex, lambda option: option, "OptionData")
    before_items = _unique_mapping(before.OptionsByItemType, lambda record: record[0], lambda record: record[1], "OptionsByItemType")
    after_items = _unique_mapping(after.OptionsByItemType, lambda record: record[0], lambda record: record[1], "OptionsByItemType")

    def option_summary(record_id: str, old: Any, new: Any, values: tuple[ValueChange, ...]) -> str:
        if len(values) == 1 and ".TierValue[" in values[0].field_path:
            value = values[0]
            tier = value.field_path.split("[", 1)[1].split("]", 1)[0]
            option_id = record_id.removeprefix("OptionData:")
            return f"옵션 ID {option_id}의 {tier}티어 값이 {value.before!r}에서 {value.after!r}(으)로 변경되었습니다."
        return f"{record_id}의 웹 관련 필드 {len(values)}개가 변경되었습니다."

    option_changes = _mapping_record_changes(
        before_options,
        after_options,
        _instandard_option_values,
        id_prefix="OptionData:",
        summary_for_change=option_summary,
    )

    def item_values(old: list[int], new: list[int]) -> tuple[ValueChange, ...]:
        values = [
            ValueChange(f"option_ids (-{option_id})", option_id, None)
            for option_id in sorted(set(old) - set(new))
        ]
        values.extend(
            ValueChange(f"option_ids (+{option_id})", None, option_id)
            for option_id in sorted(set(new) - set(old))
        )
        if not values and old != new:
            values.append(ValueChange("option_ids", _plain(old), _plain(new)))
        return tuple(values)

    item_changes = _mapping_record_changes(
        before_items,
        after_items,
        item_values,
        id_prefix="OptionsByItemType:",
        summary_for_change=lambda record_id, old, new, values: (
            f"장비 종류 {record_id.removeprefix('OptionsByItemType:')}의 옵션 연결 {len(values)}개가 변경되었습니다."
        ),
    )
    collection_counts = (
        ("OptionData", len(before.OptionData), len(after.OptionData)),
        ("OptionsByItemType", len(before.OptionsByItemType), len(after.OptionsByItemType)),
    )
    return RecordDiff(
        relative_path,
        sum(item[1] for item in collection_counts),
        sum(item[2] for item in collection_counts),
        option_changes + item_changes,
        collection_counts,
        "비규격 옵션, 티어 값, 장비 종류별 옵션 연결",
        "MaterialData, PrefixTagName, DisJointData와 파서가 해석하지 않는 바이트 영역",
    )


_RECORD_DIFFERS: dict[str, Callable[[Path, Path, Path], RecordDiff]] = {
    "capa.dat": _capa_diff,
    "simplegametext.dat": _item_groups_diff,
    "item_option_open.dat": _item_option_open_diff,
    "instandardequip.dat": _instandard_equip_diff,
}


def _add_record_diff(
    relative_path: Path,
    before_path: Path,
    after_path: Path,
    report: ComparisonReport,
) -> bool:
    differ = _RECORD_DIFFERS.get(relative_path.name.lower())
    if differ is None:
        return True
    report.inspected_paths.append(relative_path)
    try:
        report.record_diffs.append(differ(relative_path, before_path, after_path))
    except Exception as error:
        report.parse_failures.add(relative_path)
        report.warnings.append(f"파일을 파싱할 수 없습니다: {relative_path} ({error})")
        recommendation = f"{relative_path}: 파싱 실패 원인과 자동 검사가 놓친 변경을 추가 검사해야 합니다."
        if recommendation not in report.recommended_codex_checks:
            report.recommended_codex_checks.append(recommendation)
        return False
    return True


def compare_directories(
    before_root: Path,
    after_root: Path,
    *,
    require_complete_inputs: bool = False,
) -> ComparisonReport:
    """대상 파일을 비교한다. 실제 명령은 필수 입력 사전 검사를 사용한다."""
    report = ComparisonReport()
    invalid_roots = [root for root in (before_root, after_root) if not root.is_dir()]
    if invalid_roots:
        report.warnings.extend(f"스냅샷 경로가 디렉터리가 아닙니다: {root}" for root in invalid_roots)
        report.fatal_error = require_complete_inputs
        return report

    if require_complete_inputs and not _preflight_required_files(
        before_root, after_root, report
    ):
        return report

    before_files = _target_files(before_root)
    after_files = _target_files(after_root)
    for relative_path in sorted(before_files.keys() | after_files.keys()):
        before = before_files.get(relative_path)
        after = after_files.get(relative_path)
        if before is None:
            after_data = _read_file(after, report)
            result = FileChange(relative_path, "추가", after_size=after_data[0] if after_data else None, after_sha256=after_data[1] if after_data else None)
            report.changes.append(result)
            report.file_results.append(result)
            continue
        if after is None:
            before_data = _read_file(before, report)
            result = FileChange(relative_path, "삭제", before_size=before_data[0] if before_data else None, before_sha256=before_data[1] if before_data else None)
            report.changes.append(result)
            report.file_results.append(result)
            continue

        before_data = _read_file(before, report)
        after_data = _read_file(after, report)
        if before_data is None or after_data is None:
            if require_complete_inputs:
                report.fatal_error = True
                return report
            continue
        changed = before_data[1] != after_data[1]
        if changed:
            byte_diff = None
            if relative_path.name.lower() in DETAIL_FILE_NAMES:
                try:
                    byte_diff = _byte_diff(before, after)
                except OSError as error:
                    report.warnings.append(f"바이트를 비교할 수 없습니다: {relative_path} ({error})")
                    if require_complete_inputs:
                        report.fatal_error = True
                        return report
            result = FileChange(relative_path, "수정", before_data[0], after_data[0], before_data[1], after_data[1], byte_diff)
            report.changes.append(result)
            report.file_results.append(result)
        else:
            report.unchanged_count += 1
            report.file_results.append(FileChange(relative_path, "동일", before_data[0], after_data[0], before_data[1], after_data[1]))

        name = relative_path.name.lower()
        if name in DETAIL_FILE_NAMES:
            parsed = _add_record_diff(relative_path, before, after, report)
            if require_complete_inputs and not parsed:
                report.fatal_error = True
                return report
        # japanese.llt는 의도적으로 파싱하지 않는다.

    changed_paths = {change.relative_path for change in report.changes if change.status == "수정"}
    diff_by_path = {diff.relative_path: diff for diff in report.record_diffs}
    for path in sorted(changed_paths):
        if path.name.lower() not in DETAIL_FILE_NAMES:
            continue
        record_diff = diff_by_path.get(path)
        if record_diff is not None and not record_diff.changes:
            report.recommended_codex_checks.append(
                f"{path}: 파일은 변경됐지만 자동 검사 기준 웹 관련 레코드는 동일합니다. 추가 검사를 추천합니다."
            )
    return report


def _counts(report: ComparisonReport) -> dict[str, int]:
    return {status: sum(change.status == status for change in report.changes) for status in ("추가", "삭제", "수정")}


def render_report(report: ComparisonReport) -> str:
    """터미널에 표시할 짧은 한국어 요약을 만든다."""
    counts = _counts(report)
    total_record_changes = sum(len(diff.changes) for diff in report.record_diffs)
    lines = [
        "Data 비교 보고서",
        f"상태: {report.status}",
        f"파일: 추가 {counts['추가']}, 삭제 {counts['삭제']}, 수정 {counts['수정']}, 동일 {report.unchanged_count}",
        f"웹 관련 레코드 변경: {total_record_changes}건",
    ]
    for change in report.changes:
        size = f" ({change.before_size} B → {change.after_size} B)" if change.status == "수정" else ""
        if change.relative_path.name.lower() == JAPANESE_FILE_NAME and change.status == "수정":
            lines.append(f"japanese.llt: 변경됨 - 한국어 중심 검사 범위에서 상세 분석 제외")
        else:
            lines.append(f"[{change.status}] {change.relative_path}{size}")
        record_diff = next((diff for diff in report.record_diffs if diff.relative_path == change.relative_path), None)
        if record_diff is not None:
            lines.extend(
                f"  {name}: {before_count} → {after_count}"
                for name, before_count, after_count in record_diff.collection_counts
            )
            if not record_diff.changes:
                lines.append(f"  자동 검사 기준 웹 관련 변경 없음 (파싱된 레코드 {record_diff.after_count}개는 동일)")
    if report.warnings:
        lines.append(f"경고: {len(report.warnings)}개")
        lines.extend(f"- {warning}" for warning in report.warnings)
    if report.recommended_codex_checks:
        lines.append(f"Codex 추가 검사 추천: {len(report.recommended_codex_checks)}건")
    return "\n".join(lines)


def report_to_dict(report: ComparisonReport) -> dict[str, Any]:
    diff_by_path = {diff.relative_path: diff for diff in report.record_diffs}
    result_by_path = {result.relative_path: result for result in report.file_results}
    all_paths = sorted(set(report.inspected_paths) | set(result_by_path))
    files: list[dict[str, Any]] = []
    for path in all_paths:
        file_change = result_by_path.get(path)
        record_diff = diff_by_path.get(path)
        is_japanese = path.name.lower() == JAPANESE_FILE_NAME
        files.append(
            {
                "file": path.as_posix(),
                "file_status": file_change.status if file_change else "검사 실패",
                "inspection_success": path not in report.parse_failures,
                "inspection_mode": "해시 변경 여부만 검사" if is_japanese else "한국어 웹 관련 레코드 상세 비교",
                "understood_scope": record_diff.understood_scope if record_diff else ("전체 파일 SHA-256 해시" if is_japanese else "지원하지 않는 파일"),
                "compared_records": {
                    "before": record_diff.before_count,
                    "after": record_diff.after_count,
                } if record_diff else None,
                "uninspected_scope": record_diff.uninspected_scope if record_diff else ("파일 내부 전체" if is_japanese else "레코드 상세"),
                "before_size": file_change.before_size if file_change else None,
                "after_size": file_change.after_size if file_change else None,
                "before_sha256": file_change.before_sha256 if file_change else None,
                "after_sha256": file_change.after_sha256 if file_change else None,
                "byte_comparison": _plain(file_change.byte_diff) if file_change and file_change.byte_diff else None,
                "web_related_change": bool(record_diff and record_diff.changes),
            }
        )

    changes: list[dict[str, Any]] = []
    for record_diff in report.record_diffs:
        for change in record_diff.changes:
            changes.append(
                {
                    "file": record_diff.relative_path.as_posix(),
                    "status": change.status,
                    "record_id": change.record_id,
                    "changed_fields": list(change.fields),
                    "values": [_plain(value) for value in change.values],
                    "korean_name": change.korean_name,
                    "summary": change.summary,
                    "evidence": [
                        {
                            "record_id": change.record_id,
                            "field_path": value.field_path,
                            "before": _plain(value.before),
                            "after": _plain(value.after),
                        }
                        for value in change.values
                    ],
                }
            )
    return {
        "inspection_scope": "한국어 웹 데이터",
        "status": report.status,
        "limitations": LIMITATIONS,
        "files": files,
        "changes": changes,
        "warnings": list(report.warnings),
        "errors": list(report.warnings),
        "recommended_codex_checks": list(report.recommended_codex_checks),
    }


def _markdown_value(value: Any) -> str:
    return json.dumps(_plain(value), ensure_ascii=False, sort_keys=True)


def render_markdown(report: ComparisonReport) -> str:
    data = report_to_dict(report)
    lines = [
        "# 게임 데이터 업데이트 검사 보고서",
        "",
        f"> 상태: **{report.status}**",
    ]
    if report.warnings:
        lines.extend(("", "> 일부 파일을 읽거나 파싱하지 못했습니다. 아래 경고와 오류를 확인하세요."))
    lines.extend((
        "",
        "## 검사 범위",
        "",
        "한국어 웹 데이터에 쓰이는 4개 `.dat` 파일을 상세 비교합니다. `japanese.llt`는 해시만 비교합니다.",
        "",
        "### 한계",
        "",
    ))
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.extend(("", "## 파일별 검사 결과", ""))
    for item in data["files"]:
        lines.extend((
            f"### `{item['file']}`",
            "",
            f"- 파일 상태: {item['file_status']}",
            f"- 검사 성공: {'예' if item['inspection_success'] else '아니요'}",
            f"- 검사 방식: {item['inspection_mode']}",
            f"- 파서가 이해한 범위: {item['understood_scope']}",
            f"- 검사하지 못한 영역: {item['uninspected_scope']}",
        ))
        if item["compared_records"]:
            counts = item["compared_records"]
            lines.append(f"- 비교한 레코드 수: {counts['before']} → {counts['after']}")
        byte_diff = item["byte_comparison"]
        if byte_diff:
            first = byte_diff["first_change_offset"]
            lines.extend((
                f"- 동일 offset 기준 불일치 바이트: {byte_diff['offset_mismatch_bytes']}개",
                f"- 변경 구간: {byte_diff['changed_regions']}개",
                f"- 첫 변경 위치: 0x{first:06X}" if first is not None else "- 첫 변경 위치: 없음",
            ))
        if item["file"].lower().endswith(JAPANESE_FILE_NAME) and item["file_status"] == "수정":
            lines.append("- japanese.llt: 변경됨 - 한국어 중심 검사 범위에서 상세 분석 제외")
        if (
            item["file_status"] == "수정"
            and item["inspection_success"]
            and not item["web_related_change"]
            and not item["file"].lower().endswith(JAPANESE_FILE_NAME)
        ):
            lines.append("- 자동 검사 기준 웹 관련 변경 없음")
        lines.append("")

    lines.extend(("## 전체 웹 관련 변경", ""))
    if not data["changes"]:
        lines.extend(("자동 검사 기준 웹 관련 변경 없음", ""))
    for index, change in enumerate(data["changes"], 1):
        lines.extend((
            f"### {index}. [{change['status']}] `{change['file']}` / `{change['record_id']}`",
            "",
        ))
        if change["korean_name"]:
            lines.append(f"- 한국어 이름: {change['korean_name']}")
        lines.extend((
            f"- 자연어 요약: {change['summary']}",
            "- 정확한 구조적 근거:",
            "",
        ))
        for evidence in change["evidence"]:
            lines.extend((
                f"  - `{evidence['record_id']}`",
                f"    - 필드 경로: `{evidence['field_path']}`",
                f"    - 변경 전: `{_markdown_value(evidence['before'])}`",
                f"    - 변경 후: `{_markdown_value(evidence['after'])}`",
            ))
        lines.append("")

    lines.extend(("## 경고와 오류", ""))
    lines.extend(f"- {warning}" for warning in report.warnings)
    if not report.warnings:
        lines.extend(("없음", ""))
    else:
        lines.append("")
    lines.extend(("## Codex 추가 검사 추천", ""))
    if report.recommended_codex_checks:
        lines.extend(f"- {item}" for item in report.recommended_codex_checks)
    else:
        lines.append("자동 검사에서 별도로 추천한 항목이 없습니다. 그래도 이 결과는 완전한 판정이 아닙니다.")
    lines.extend((
        "",
        "## Codex 추가 분석 요청문",
        "",
        "```text",
        "before/와 after/를 추가 분석해 주세요.",
        "먼저 이 폴더의 report.md와 report.json을 읽어 주세요.",
        "자동 검사에서 놓친 구조 변경과 알 수 없는 ID를 확인해 주세요.",
        "한국어 변경 내용을 검증해 주세요.",
        "확인된 내용을 바탕으로 한국어와 일본어 웹 렌더링 반영 방법을 제안해 주세요.",
        "```",
        "",
    ))
    return "\n".join(lines)
