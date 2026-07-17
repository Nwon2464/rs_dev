from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import compare_data
from rs_dev import data_diff
from rs_dev.data_diff import compare_directories, render_report


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


def test_cli_accepts_snapshot_paths_and_returns_zero_for_file_changes(tmp_path: Path) -> None:
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

    assert result.returncode == 0
    assert "[수정] unsupported.dat" in result.stdout


def test_cli_returns_one_for_parse_error_without_losing_file_change(tmp_path: Path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "capa.dat").write_bytes(b"old")
    (after / "capa.dat").write_bytes(b"new")
    script = Path(__file__).resolve().parents[1] / "scripts" / "compare_data.py"

    result = subprocess.run(
        [sys.executable, str(script), str(before), str(after)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "[수정] capa.dat" in result.stdout
    assert "파일을 파싱할 수 없습니다: capa.dat" in result.stdout


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
    assert record_diff.changes[0].fields == ("name", "help_text")
    assert record_diff.changes[1].status == "삭제"
    output = render_report(report)
    assert "레코드: 2 → 12" in output
    assert "추가 11, 삭제 1, 수정 1" in output
    assert "수정 0: name, help_text" in output
    assert "상세 변경 외 3건" in output


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

    assert (record_diff.before_count, record_diff.after_count) == (6, 6)
    assert record_diff.collection_counts == (
        ("OptionData", 1, 1),
        ("OptionsByItemType", 1, 1),
        ("MaterialData", 1, 1),
        ("PrefixTagName", 2, 2),
        ("DisJointData", 1, 1),
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
        ("MaterialData:5", ("GoldBarCost",)),
        ("PrefixTagName:1", ("text",)),
        ("DisJointData:0", ("ItemCountRange[1]",)),
    ]
    output = render_report(compare_directories(before, after))
    assert "OptionData: 1 → 1" in output
    assert "수정 OptionData:63: TagName" in output


def test_japanese_llt_diff_uses_composite_key_and_only_contract_fields(
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

    monkeypatch.setattr(
        data_diff,
        "parse_japanese_llt",
        lambda path: [record(100003, "new", 3), record(100005, "added")]
        if path.parent == after
        else [record(100003, "old", 2), record(100004, "removed")],
    )

    record_diff = compare_directories(before, after).record_diffs[0]

    assert (record_diff.before_count, record_diff.after_count) == (2, 2)
    assert [(change.status, change.record_id, change.fields) for change in record_diff.changes] == [
        ("수정", "10/100003/0/0", ("text", "kind")),
        ("삭제", "10/100004/0/0", ()),
        ("추가", "10/100005/0/0", ()),
    ]


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
        (
            "MaterialData",
            lambda _option: [
                {"MaterialIdx": 5, "GoldBarCost": 10},
                {"MaterialIdx": 5, "GoldBarCost": 20},
            ],
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


def test_japanese_llt_duplicate_key_fails_only_record_details(
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
    monkeypatch.setattr(
        data_diff,
        "parse_japanese_llt",
        lambda path: [record, record] if path.parent == after else [record],
    )

    report = compare_directories(before, after)

    assert [(change.relative_path.name, change.status) for change in report.changes] == [
        ("japanese.llt", "수정")
    ]
    assert not report.record_diffs
    assert any("중복 레코드 키: japanese.llt:" in warning for warning in report.warnings)


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
        "simpleGameText.dat"
    ]
    assert any("MaterialIdx" in warning for warning in report.warnings)


def test_material_field_added_with_none_is_reported_as_modified(
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

    assert [(change.status, change.record_id, change.fields) for change in record_diff.changes] == [
        ("수정", "MaterialData:5", ("GoldBarCost",))
    ]
