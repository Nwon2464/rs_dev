"""Build the Japanese option-template catalog from japanese.llt section 22."""

from __future__ import annotations

from collections.abc import Iterable

from rs_dev.japanese_base_options import build_japanese_base_options
from rs_dev.models import JapaneseLltRecord
from rs_dev.open_options.templates.normalize import normalize_template


def build_japanese_catalog(records: Iterable[JapaneseLltRecord]) -> dict[int, str]:
    return {
        option_id: normalize_template(template)
        for option_id, template in build_japanese_base_options(records).items()
        if normalize_template(template)
    }
