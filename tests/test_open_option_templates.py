from __future__ import annotations

import pytest

from rs_dev.open_options.templates.placeholders import placeholder_indices, title_template
from rs_dev.open_options.templates.render import render_template


def test_title_placeholders_preserve_sign_suffix_and_repetition() -> None:
    assert title_template("武器最小攻撃力 +[0]") == "武器最小攻撃力 +[n]"
    assert title_template("力 [+0] [1]秒") == "力 [+n1] [n2]秒"
    assert title_template("[0] / [1] / [0]") == "[n1] / [n2] / [n1]"
    assert title_template("物理攻撃力増加 [0%]") == "物理攻撃力増加 [n%]"


def test_render_supports_signed_precision_and_full_width_percent() -> None:
    assert render_template("このアイテムの着用レベル [-0]", [300, 0]) == "このアイテムの着用レベル -300"
    assert render_template("吸血 [+1.1％]", [0, 35]) == "吸血 +3.5％"
    assert placeholder_indices("[0] [+1.1%] [-2]") == [0, 1, 2]


def test_explicit_value_binding_reuses_primary_value() -> None:
    template = "物理 +[0]、魔法 +[1]"
    assert render_template(template, [20, 0, 0], {1: 0}) == "物理 +20、魔法 +20"
    assert title_template(template) == "物理 +[n1]、魔法 +[n2]"


def test_missing_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="unavailable"):
        render_template("[2]", [1, 2])
