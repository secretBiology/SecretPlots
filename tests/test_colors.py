import pytest

import SecretPlots as sp
from SecretPlots.core.colors import extend_palette, readable_on, text_pair

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


def test_text_pair_suits_light_and_dark_themes() -> None:
    assert text_pair("#262626", "#ffffff") == ("#262626", "#ffffff")
    assert text_pair("#f4f4f4", "#161616") == ("#161616", "#f4f4f4")


def test_dark_heatmap_values_stay_readable_on_pale_cells() -> None:
    plot = sp.heatmap([[0.0, 1.0], [-1.0, 0.0]]).cmap("tol_bu_rd", center=0)
    plot = plot.values(".1f").theme("dark")
    plot.render()
    pale = [t for t in plot.ax.texts if t.get_text() == "0.0"]
    assert pale
    assert all(t.get_color() == "#161616" for t in pale)
