from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import compare_data
from rs_dev import data_diff
from rs_dev.data_diff import (
    compare_directories,
    render_markdown,
    render_report,
    report_to_dict,
)


def test_compares_dat_and_japanese_llt_by_recursive_relative_path(tmp_path: Path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    (before / "language").mkdir(parents=True)
    (after / "language").mkdir(parents=True)
    (before / "same.DAT").write_bytes(b"same")
    (after / "same.DAT").write_bytes(b"same")
    (before / "language" / "japanese.llt").write_bytes(b"old")
    (after / "language" / "japanese.llt").write_bytes(b"new")
    (before / "removed.dat").write_bytes(b"before")
    (after / "added.dat").write_bytes(b"after")
    (after / "language" / "other.llt").write_bytes(b"ignored")

    report = compare_directories(before, after)

    assert report.unchanged_count == 1
    assert [(change.relative_path.as_posix(), change.status) for change in report.changes] == [
        ("added.dat", "추가"),
        ("language/japanese.llt", "수정"),
        ("removed.dat", "삭제"),
    ]
    assert "other.llt" not in render_report(report)


def test_reports_file_size_and_korean_summary(tmp_path: Path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "capa.dat").write_bytes(b"one")
    (after / "capa.dat").write_bytes(b"longer")

    output = render_report(compare_directories(before, after))

    assert "파일: 추가 0, 삭제 0, 수정 1, 동일 0" in output
    assert "[수정] capa.dat (3 B → 6 B)" in output


def test_cli_stops_when_required_files_are_missing(tmp_path: Path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "unsupported.dat").write_bytes(b"old")
    (after / "unsupported.dat").write_bytes(b"new")
    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_data.py"

    result = subprocess.run(
        [sys.executable, str(script), str(before), str(after)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "상태: 검사 중단" in result.stdout
    assert "필수 파일이 없습니다" in result.stdout
    assert "보고서 폴더를 만들지 않았습니다" in result.stdout


def test_cli_returns_one_for_parse_error_without_creating_report(tmp_path: Path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "language").mkdir()
    (after / "language").mkdir()
    (before / "capa.dat").write_bytes(b"old")
    (after / "capa.dat").write_bytes(b"new")
    for name in ("item_option_open.dat", "InstandardEquip.dat", "simpleGameText.dat"):
        (before / name).write_bytes(b"invalid")
        (after / name).write_bytes(b"invalid")
    (before / "language" / "japanese.llt").write_bytes(b"old")
    (after / "language" / "japanese.llt").write_bytes(b"new")
    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_data.py"

    result = subprocess.run(
        [sys.executable, str(script), str(before), str(after)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "상태: 검사 중단" in result.stdout
    assert "필수 파일을 파싱할 수 없습니다" in result.stdout
    assert "capa.dat" in result.stdout
    assert "보고서 폴더를 만들지 않았습니다" in result.stdout


def test_cli_rejects_a_single_snapshot_path(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_data.py"

    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 2
    assert "경로 인자는 생략하거나 before와 after 두 개를 지정해야 합니다" in result.stderr


def test_cli_returns_one_and_warns_for_invalid_snapshot_paths(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    not_directory = tmp_path / "snapshot.dat"
    not_directory.write_bytes(b"data")
    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_data.py"

    result = subprocess.run(
        [sys.executable, str(script), str(missing), str(not_directory)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "파일: 추가 0, 삭제 0, 수정 0, 동일 0" in result.stdout
    assert f"스냅샷 경로가 디렉터리가 아닙니다: {missing}" in result.stdout
    assert f"스냅샷 경로가 디렉터리가 아닙니다: {not_directory}" in result.stdout


def test_read_error_is_collected_without_hiding_other_file_changes(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "broken.dat").write_bytes(b"old")
    (after / "broken.dat").write_bytes(b"new")
    (before / "changed.dat").write_bytes(b"one")
    (after / "changed.dat").write_bytes(b"two")
    original = data_diff._fingerprint

    def fail_for_broken(path: Path) -> tuple[int, str]:
        if path.name == "broken.dat":
            raise OSError("denied")
        return original(path)

    monkeypatch.setattr(data_diff, "_fingerprint", fail_for_broken)

    report = compare_directories(before, after)

    assert [(change.relative_path.name, change.status) for change in report.changes] == [
        ("changed.dat", "수정")
    ]
    assert len(report.warnings) == 2


def test_added_and_removed_files_remain_reported_when_reads_fail(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "removed.dat").write_bytes(b"before")
    (after / "added.dat").write_bytes(b"after")

    def fail_read(path: Path) -> tuple[int, str]:
        raise OSError(f"denied {path.name}")

    monkeypatch.setattr(data_diff, "_fingerprint", fail_read)

    report = compare_directories(before, after)

    assert [(change.relative_path.name, change.status) for change in report.changes] == [
        ("added.dat", "추가"),
        ("removed.dat", "삭제"),
    ]
    assert len(report.warnings) == 2
    output = render_report(report)
    assert "[추가] added.dat" in output
    assert "[삭제] removed.dat" in output


def test_capa_record_diff_reports_add_remove_modified_fields_and_limit(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "capa.dat").write_bytes(b"before")
    (after / "capa.dat").write_bytes(b"after")

    before_records = {
        0: {
            "name": "old",
            "description": "same",
            "short_text": "s",
            "help_text": "h",
        },
        1: {
            "name": "removed",
            "description": "",
            "short_text": "",
            "help_text": "",
        },
    }
    after_records = {
        0: {
            "name": "new",
            "description": "same",
            "short_text": "s",
            "help_text": "changed",
        },
        **{
            record_id: {
                "name": str(record_id),
                "description": "",
                "short_text": "",
                "help_text": "",
            }
            for record_id in range(2, 13)
        },
    }

    monkeypatch.setattr(
        data_diff,
        "parse_capa",
        lambda path: before_records if path.parent == before else after_records,
    )

    report = compare_directories(before, after)
    record_diff = report.record_diffs[0]

    assert (record_diff.before_count, record_diff.after_count) == (2, 12)
    assert record_diff.changes[0].record_id == "0"
    # help_text는 현재 웹에서 사용하지 않으므로 상세 비교에서 제외한다.
    assert record_diff.changes[0].fields == ("name",)
    assert record_diff.changes[1].status == "삭제"
    assert set(record_diff.changes[1].values[0].before) == {
        "name", "description", "short_text"
    }
    assert "help_text" not in record_diff.changes[1].values[0].before
    assert "record_offset" not in record_diff.changes[1].values[0].before
    assert set(record_diff.changes[2].values[0].after) == {
        "name", "description", "short_text"
    }
    output = render_report(report)
    assert "웹 관련 레코드 변경: 13건" in output


def test_simple_game_text_record_diff_uses_group_id_and_name(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "simpleGameText.dat").write_bytes(b"before")
    (after / "simpleGameText.dat").write_bytes(b"after")

    monkeypatch.setattr(
        data_diff,
        "parse_item_groups",
        lambda path: {1: "old", 2: "removed"}
        if path.parent == before
        else {1: "new", 3: "added"},
    )

    record_diff = compare_directories(before, after).record_diffs[0]

    assert [
        (change.status, change.record_id, change.fields)
        for change in record_diff.changes
    ] == [("수정", "1", ("name",)), ("삭제", "2", ()), ("추가", "3", ())]


def test_item_option_open_diff_summarizes_nested_rows_by_block(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "item_option_open.dat").write_bytes(b"before")
    (after / "item_option_open.dat").write_bytes(b"after")

    def block(
        index: int,
        rows: list[SimpleNamespace],
        group_ids: tuple[int, ...] = (),
    ) -> SimpleNamespace:
        return SimpleNamespace(
            block_index=index,
            section_type=7,
            section_group=1,
            group_ids=group_ids,
            rows=rows,
        )

    def row(index: int, option_id: int) -> SimpleNamespace:
        return SimpleNamespace(
            row_index=index,
            candidate_index=1,
            option_id=option_id,
            packed_value=0,
            float_a=1.0,
            float_b=2.0,
            tier=3,
        )

    monkeypatch.setattr(
        data_diff,
        "parse_item_option_open",
        lambda path: [block(0, [row(1, 10)]), block(1, [])]
        if path.parent == before
        else [block(0, [row(1, 20), row(2, 30)], (9,)), block(2, [])],
    )

    record_diff = compare_directories(before, after).record_diffs[0]

    assert [(change.status, change.record_id) for change in record_diff.changes] == [
        ("수정", "block:0"),
        ("삭제", "block:1"),
        ("추가", "block:2"),
    ]
    assert record_diff.changes[0].fields == (
        "group_ids",
        "rows[1].option_id",
        "rows[2]",
    )
    assert record_diff.collection_counts == (("행", 1, 2),)
    assert "행: 1 → 2" in render_report(compare_directories(before, after))


def test_parse_error_keeps_file_change_and_other_record_diffs(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "capa.dat").write_bytes(b"old")
    (after / "capa.dat").write_bytes(b"new")
    (before / "simpleGameText.dat").write_bytes(b"old")
    (after / "simpleGameText.dat").write_bytes(b"new")

    monkeypatch.setattr(
        data_diff,
        "parse_capa",
        lambda path: (_ for _ in ()).throw(ValueError("bad capa")),
    )
    monkeypatch.setattr(
        data_diff,
        "parse_item_groups",
        lambda path: {0: "before"} if path.parent == before else {0: "after"},
    )

    report = compare_directories(before, after)

    assert [change.relative_path.name for change in report.changes] == [
        "capa.dat",
        "simpleGameText.dat",
    ]
    assert [diff.relative_path.name for diff in report.record_diffs] == ["simpleGameText.dat"]
    assert "파일을 파싱할 수 없습니다: capa.dat (bad capa)" in report.warnings


def test_instandard_equip_diff_uses_collection_keys_and_nested_field_paths(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "InstandardEquip.dat").write_bytes(b"before")
    (after / "InstandardEquip.dat").write_bytes(b"after")

    def option(option_id: int, tag: str, value: int) -> SimpleNamespace:
        return SimpleNamespace(
            OptionCapaIndex=option_id,
            TagName=[tag],
            TierData=[
                SimpleNamespace(
                    Tier=3,
                    OptionLevel=1,
                    TierValue=[(value, 0, 0)] * 10,
                )
            ],
        )

    def parsed(*, is_after: bool) -> SimpleNamespace:
        return SimpleNamespace(
            OptionData=[option(63, "new" if is_after else "old", 2 if is_after else 1)],
            OptionsByItemType=[(7, [100, 901] if is_after else [100, 900])],
            MaterialData=[
                {"MaterialIdx": 5, "GoldBarCost": 20 if is_after else 10,
                 "MaterialItemCount": 2}
            ],
            PrefixTagName=["same", "new" if is_after else "old"],
            DisJointData=[
                {"DisjointCondition": 1, "Grade": 2,
                 "ItemCountRange": [1, 3 if is_after else 2], "ItemIndex": 9}
            ],
        )

    monkeypatch.setattr(
        data_diff,
        "parse_instandard_equip",
        lambda path: parsed(is_after=path.parent == after),
    )

    record_diff = compare_directories(before, after).record_diffs[0]

    # 현재 웹에서 사용하는 두 컬렉션만 상세 비교 개수에 포함한다.
    assert (record_diff.before_count, record_diff.after_count) == (2, 2)
    assert record_diff.collection_counts == (
        ("OptionData", 1, 1),
        ("OptionsByItemType", 1, 1),
    )
    assert [(change.record_id, change.fields) for change in record_diff.changes] == [
        (
            "OptionData:63",
            ("TagName", "TierData[3].TierValue[0][0]", "TierData[3].TierValue[1][0]",
             "TierData[3].TierValue[2][0]", "TierData[3].TierValue[3][0]",
             "TierData[3].TierValue[4][0]", "TierData[3].TierValue[5][0]",
             "TierData[3].TierValue[6][0]", "TierData[3].TierValue[7][0]",
             "TierData[3].TierValue[8][0]", "TierData[3].TierValue[9][0]"),
        ),
        ("OptionsByItemType:7", ("option_ids (-900)", "option_ids (+901)")),
    ]
    output = render_report(compare_directories(before, after))
    assert "OptionData: 1 → 1" in output


def test_japanese_llt_uses_hash_only_and_is_not_parsed(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "japanese.llt").write_bytes(b"before")
    (after / "japanese.llt").write_bytes(b"after")

    def record(text_id: int, text: str, kind: int = 2) -> SimpleNamespace:
        return SimpleNamespace(
            section_id=10,
            text_id=text_id,
            variant_id=0,
            sub_variant_id=0,
            text=text,
            kind=kind,
        )

    report = compare_directories(before, after)

    assert not report.record_diffs
    assert report.changes[0].status == "수정"
    assert "상세 분석 제외" in render_report(report)


def test_instandard_parse_error_keeps_file_level_change(tmp_path: Path, monkeypatch) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "InstandardEquip.dat").write_bytes(b"before")
    (after / "InstandardEquip.dat").write_bytes(b"after")
    monkeypatch.setattr(
        data_diff,
        "parse_instandard_equip",
        lambda _path: (_ for _ in ()).throw(ValueError("bad InstandardEquip")),
    )

    report = compare_directories(before, after)

    assert [change.relative_path.name for change in report.changes] == ["InstandardEquip.dat"]
    assert not report.record_diffs
    assert "파일을 파싱할 수 없습니다: InstandardEquip.dat (bad InstandardEquip)" in report.warnings


@pytest.mark.parametrize(
    ("collection_name", "duplicate_records"),
    [
        (
            "OptionData",
            lambda option: [option, option],
        ),
        (
            "OptionsByItemType",
            lambda _option: [(7, [100]), (7, [101])],
        ),
    ],
)
def test_instandard_duplicate_collection_keys_fail_only_record_details(
    tmp_path: Path, monkeypatch, collection_name: str, duplicate_records
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "InstandardEquip.dat").write_bytes(b"before")
    (after / "InstandardEquip.dat").write_bytes(b"after")
    option = SimpleNamespace(OptionCapaIndex=63, TagName=[], TierData=[])

    def parsed(is_after: bool) -> SimpleNamespace:
        values = {
            "OptionData": [option],
            "OptionsByItemType": [],
            "MaterialData": [],
            "PrefixTagName": [],
            "DisJointData": [],
        }
        if is_after:
            values[collection_name] = duplicate_records(option)
        return SimpleNamespace(**values)

    monkeypatch.setattr(
        data_diff,
        "parse_instandard_equip",
        lambda path: parsed(path.parent == after),
    )

    report = compare_directories(before, after)

    assert [(change.relative_path.name, change.status) for change in report.changes] == [
        ("InstandardEquip.dat", "수정")
    ]
    assert not report.record_diffs
    assert any(f"중복 레코드 키: {collection_name}:" in warning for warning in report.warnings)


def test_instandard_duplicate_tier_keys_fail_only_record_details(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "InstandardEquip.dat").write_bytes(b"before")
    (after / "InstandardEquip.dat").write_bytes(b"after")
    tier = SimpleNamespace(Tier=3, OptionLevel=1, TierValue=[])

    def parsed(is_after: bool) -> SimpleNamespace:
        option = SimpleNamespace(
            OptionCapaIndex=63,
            TagName=[],
            TierData=[tier, tier] if is_after else [tier],
        )
        return SimpleNamespace(
            OptionData=[option],
            OptionsByItemType=[],
            MaterialData=[],
            PrefixTagName=[],
            DisJointData=[],
        )

    monkeypatch.setattr(
        data_diff,
        "parse_instandard_equip",
        lambda path: parsed(path.parent == after),
    )

    report = compare_directories(before, after)

    assert not report.record_diffs
    assert any("중복 레코드 키: OptionData.TierData:3" in warning for warning in report.warnings)


@pytest.mark.parametrize(
    "duplicate_side",
    [pytest.param("after", id="added-option"), pytest.param("before", id="removed-option")],
)
def test_instandard_added_or_removed_option_validates_duplicate_tier_keys(
    tmp_path: Path, monkeypatch, duplicate_side: str
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "InstandardEquip.dat").write_bytes(b"before")
    (after / "InstandardEquip.dat").write_bytes(b"after")
    tier = SimpleNamespace(Tier=3, OptionLevel=1, TierValue=[])
    duplicate_option = SimpleNamespace(
        OptionCapaIndex=64,
        TagName=[],
        TierData=[tier, tier],
    )

    def parsed(path: Path) -> SimpleNamespace:
        side = "after" if path.parent == after else "before"
        return SimpleNamespace(
            OptionData=[duplicate_option] if side == duplicate_side else [],
            OptionsByItemType=[],
            MaterialData=[],
            PrefixTagName=[],
            DisJointData=[],
        )

    monkeypatch.setattr(data_diff, "parse_instandard_equip", parsed)

    report = compare_directories(before, after)

    assert [(change.relative_path.name, change.status) for change in report.changes] == [
        ("InstandardEquip.dat", "수정")
    ]
    assert not report.record_diffs
    assert any("중복 레코드 키: OptionData.TierData:3" in warning for warning in report.warnings)
    monkeypatch.setattr(sys, "argv", ["compare_data.py", str(before), str(after)])
    assert compare_data.main() == 1


def test_japanese_llt_contents_are_not_parsed(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "japanese.llt").write_bytes(b"before")
    (after / "japanese.llt").write_bytes(b"after")
    record = SimpleNamespace(
        section_id=10,
        text_id=100003,
        variant_id=0,
        sub_variant_id=0,
        text="text",
        kind=2,
    )
    report = compare_directories(before, after)

    assert [(change.relative_path.name, change.status) for change in report.changes] == [
        ("japanese.llt", "수정")
    ]
    assert not report.record_diffs
    assert not report.warnings


def test_missing_material_index_warns_and_other_files_continue(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    for name in ("InstandardEquip.dat", "simpleGameText.dat"):
        (before / name).write_bytes(b"before")
        (after / name).write_bytes(b"after")
    parsed = SimpleNamespace(
        OptionData=[],
        OptionsByItemType=[],
        MaterialData=[{"GoldBarCost": 10}],
        PrefixTagName=[],
        DisJointData=[],
    )
    monkeypatch.setattr(data_diff, "parse_instandard_equip", lambda _path: parsed)
    monkeypatch.setattr(
        data_diff,
        "parse_item_groups",
        lambda path: {1: "before"} if path.parent == before else {1: "after"},
    )

    report = compare_directories(before, after)

    assert [change.relative_path.name for change in report.changes] == [
        "InstandardEquip.dat",
        "simpleGameText.dat",
    ]
    assert [diff.relative_path.name for diff in report.record_diffs] == [
        "InstandardEquip.dat", "simpleGameText.dat"
    ]
    assert not report.warnings
    assert any("InstandardEquip.dat" in item for item in report.recommended_codex_checks)


def test_material_field_change_is_excluded_from_web_related_changes(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "InstandardEquip.dat").write_bytes(b"before")
    (after / "InstandardEquip.dat").write_bytes(b"after")

    def parsed(is_after: bool) -> SimpleNamespace:
        material = {"MaterialIdx": 5}
        if is_after:
            material["GoldBarCost"] = None
        return SimpleNamespace(
            OptionData=[],
            OptionsByItemType=[],
            MaterialData=[material],
            PrefixTagName=[],
            DisJointData=[],
        )

    monkeypatch.setattr(
        data_diff,
        "parse_instandard_equip",
        lambda path: parsed(path.parent == after),
    )

    record_diff = compare_directories(before, after).record_diffs[0]

    assert not record_diff.changes


def test_structured_reports_include_values_byte_diff_scope_and_prompt(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "capa.dat").write_bytes(b"abcde")
    (after / "capa.dat").write_bytes(b"axcye")
    before_record = {
        1: {"name": "이전", "description": "설명", "short_text": "짧게", "help_text": "옛 도움말"}
    }
    after_record = {
        1: {"name": "이후", "description": "설명", "short_text": "짧게", "help_text": "새 도움말"}
    }
    monkeypatch.setattr(
        data_diff,
        "parse_capa",
        lambda path: before_record if path.parent == before else after_record,
    )

    report = compare_directories(before, after)
    structured = report_to_dict(report)
    markdown = render_markdown(report)

    assert structured["inspection_scope"] == "한국어 웹 데이터"
    assert structured["files"][0]["byte_comparison"] == {
        "offset_mismatch_bytes": 2,
        "changed_regions": 2,
        "first_change_offset": 1,
    }
    assert structured["changes"][0]["evidence"] == [
        {"record_id": "1", "field_path": "name", "before": "이전", "after": "이후"}
    ]
    assert "help_text" not in structured["changes"][0]["changed_fields"]
    assert "동일 offset 기준 불일치 바이트: 2개" in markdown
    assert "첫 변경 위치: 0x000001" in markdown
    assert "Codex 추가 분석 요청문" in markdown


def test_write_reports_never_overwrites_existing_folder(tmp_path: Path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    docs = tmp_path / "docs"
    before.mkdir()
    after.mkdir()
    report = compare_directories(before, after)

    first_markdown, first_json = compare_data.write_reports(report, docs)
    second_markdown, second_json = compare_data.write_reports(report, docs)

    assert first_markdown.parent != second_markdown.parent
    assert first_markdown.read_text(encoding="utf-8").startswith("# 게임 데이터")
    assert first_json.is_file()
    assert second_markdown.is_file()
    assert second_json.is_file()


def test_write_reports_does_not_create_folder_when_json_serialization_fails(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    docs = tmp_path / "docs"
    before.mkdir()
    after.mkdir()
    report = compare_directories(before, after)
    monkeypatch.setattr(compare_data, "report_to_dict", lambda _report: {"bad": object()})

    with pytest.raises(TypeError):
        compare_data.write_reports(report, docs)

    assert not docs.exists()


def test_complete_input_mode_stops_at_first_parse_failure(
    tmp_path: Path, monkeypatch
) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    for root in (before, after):
        (root / "language").mkdir(parents=True)
        for relative_path in data_diff.REQUIRED_FILES:
            (root / relative_path).write_bytes(b"data")

    calls: list[str] = []
    monkeypatch.setattr(data_diff, "parse_capa", lambda path: calls.append("capa") or {})

    def fail_item_groups(path: Path):
        calls.append("simpleGameText")
        raise ValueError("broken dependency")

    monkeypatch.setattr(data_diff, "parse_item_groups", fail_item_groups)
    monkeypatch.setattr(
        data_diff,
        "parse_item_option_open",
        lambda path: calls.append("item_option_open") or [],
    )

    report = compare_directories(
        before, after, require_complete_inputs=True
    )

    assert report.fatal_error
    assert report.status == "검사 중단"
    assert calls == ["capa", "capa", "simpleGameText"]
    assert not report.changes
    assert not report.record_diffs
