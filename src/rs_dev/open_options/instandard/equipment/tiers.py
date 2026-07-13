"""Flatten raw TierData while preserving inactive sentinels."""

from __future__ import annotations

from rs_dev.models.instandard_equipment import InstandardTierRoll, ParsedInstandardEquip


def normalize_tier_rolls(parsed: ParsedInstandardEquip) -> list[InstandardTierRoll]:
    rows: list[InstandardTierRoll] = []
    for option in parsed.OptionData:
        for tier in option.TierData:
            for roll_index, values in enumerate(tier.TierValue):
                rows.append(
                    InstandardTierRoll(
                        option_id=option.OptionCapaIndex,
                        raw_tier_index=tier.Tier,
                        option_level_raw=tier.OptionLevel,
                        enabled=tier.OptionLevel != 99999,
                        roll_index=roll_index,
                        value_0=values[0],
                        value_1=values[1],
                        value_2=values[2],
                    )
                )
    return rows
