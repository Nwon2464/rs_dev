"""Transform parsed blocks into one converter's language-neutral rows."""

from __future__ import annotations

from rs_dev.models.general_open_option import GeneralOpenOptionRow
from rs_dev.models.open_option_raw import OpenOptionBlock
from rs_dev.open_options.common.group_mapping import (
    BUCKET_BY_GROUP_IDS,
    group_names_for_signature,
)
from rs_dev.open_options.common.value_unpacking import unpack_packed_value
from rs_dev.open_options.converters.classify import converter_probability
from rs_dev.open_options.converters.specs import ConverterSpec
from rs_dev.parsers.item_option_open import ROWS_PER_SLOT


def transform_general_blocks(
    blocks: list[OpenOptionBlock],
    group_names: dict[int, str],
    spec: ConverterSpec,
) -> list[GeneralOpenOptionRow]:
    rows: list[GeneralOpenOptionRow] = []
    for block in blocks:
        if block.section_group != spec.section_group:
            continue
        if block.section_type not in spec.allowed_grade_codes:
            continue
        if block.group_ids not in BUCKET_BY_GROUP_IDS:
            continue
        joined_names = group_names_for_signature(block.group_ids, group_names)
        for raw in block.rows:
            probability = converter_probability(raw, spec)
            if probability <= 0:
                continue
            value_0, value_1 = unpack_packed_value(raw.packed_value)
            rows.append(
                GeneralOpenOptionRow(
                    converter_type=spec.converter_type,
                    equipment_bucket=BUCKET_BY_GROUP_IDS[block.group_ids],
                    group_ids=",".join(map(str, block.group_ids)),
                    group_names=",".join(joined_names),
                    grade_code=block.section_type,
                    section_group=block.section_group,
                    open_slot=raw.row_index // ROWS_PER_SLOT + 1,
                    candidate_index=raw.candidate_index,
                    option_id=raw.option_id,
                    value_0=value_0,
                    value_1=value_1,
                    probability=format(probability, ".6g"),
                    probability_source=spec.probability_source,
                    tier=raw.tier,
                    source_block_index=block.block_index,
                    source_file_offset=hex(raw.source_file_offset),
                )
            )
    return rows
