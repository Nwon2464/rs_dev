"""Transform one section_type=11 converter view."""

from __future__ import annotations

from rs_dev.models.instandard_open_option import InstandardOpenOptionRow
from rs_dev.models.open_option_raw import OpenOptionBlock
from rs_dev.open_options.common.value_unpacking import unpack_packed_value
from rs_dev.open_options.converters.classify import converter_probability
from rs_dev.open_options.converters.specs import ConverterSpec
from rs_dev.parsers.item_option_open import ROWS_PER_SLOT


SCREEN_CONFIRMED_WEAPON_SIGNATURE = (
    18, 20, 21, 22, 23, 24, 25, 26, 28, 30, 32, 33,
    54, 55, 56, 57, 58, 61, 63, 68, 70, 80, 82,
)


def transform_instandard_blocks(
    signatures: list[tuple[tuple[int, ...], dict[int, OpenOptionBlock]]],
    spec: ConverterSpec,
) -> list[InstandardOpenOptionRow]:
    rows: list[InstandardOpenOptionRow] = []
    for signature_index, (signature, blocks) in enumerate(signatures, start=1):
        block = blocks[spec.section_group]
        for item_group_id in signature:
            for raw in block.rows:
                probability = converter_probability(raw, spec)
                if probability <= 0:
                    continue
                value_0, value_1 = unpack_packed_value(raw.packed_value)
                rows.append(
                    InstandardOpenOptionRow(
                        converter_type=spec.converter_type,
                        item_group_id=item_group_id,
                        bucket_signature_index=signature_index,
                        bucket_group_ids=",".join(map(str, signature)),
                        section_type=11,
                        section_group=spec.section_group,
                        open_slot=raw.row_index // ROWS_PER_SLOT + 1,
                        candidate_index=raw.candidate_index,
                        option_id=raw.option_id,
                        value_0=value_0,
                        value_1=value_1,
                        probability=format(probability, ".9g"),
                        probability_source=spec.probability_source,
                        tier=raw.tier,
                        mapping_status=(
                            "screen_confirmed"
                            if spec.converter_type == "burning"
                            and signature == SCREEN_CONFIRMED_WEAPON_SIGNATURE
                            else "structural_candidate"
                        ),
                        source_block_index=block.block_index,
                        source_file_offset=hex(raw.source_file_offset),
                    )
                )
    return rows
