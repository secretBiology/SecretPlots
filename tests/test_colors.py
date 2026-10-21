import pytest

import SecretPlots as sp
from SecretPlots.core.colors import extend_palette, readable_on

SIX = ["#0f5499", "#eb5e8d", "#70dbed", "#9e2f50", "#4e96eb", "#96cc28"]


def test_short_request_returns_prefix_silently() -> None:
    assert extend_palette(SIX, 3, background="#ffffff") == SIX[:3]


def test_extension_is_distinct_and_keeps_originals() -> None:
    with pytest.warns(sp.PaletteExtendedWarning, match="10 categories"):
        colors = extend_palette(SIX, 10, background="#ffffff")
    assert len(set(colors)) == 10
    assert colors[:6] == SIX


def test_many_categories_hint() -> None:
    with pytest.warns(sp.PaletteExtendedWarning, match="highlight"):
        extend_palette(SIX, 12, background="#ffffff")


def test_strict_raises() -> None:
    sp.config.strict = True
    with pytest.raises(sp.PaletteExtendedWarning):
        extend_palette(SIX, 7, background="#ffffff")


def test_readable_text() -> None:
    assert readable_on("#000000", dark="#111111", light="#ffffff") == "#ffffff"
    assert readable_on("#ffffff", dark="#111111", light="#ffffff") == "#111111"
