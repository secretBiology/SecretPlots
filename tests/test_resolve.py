import pytest

import SecretPlots as sp
from SecretPlots import presets
from SecretPlots.core.merge import Layer, cascade
from SecretPlots.core.resolve import PLOT_LAYER, resolve
from SecretPlots.theme import BASE_THEME, STYLE_FIELDS, Theme, get_theme, list_themes

PLOT_KINDS = [
    "bar",
    "heatmap",
    "presence",
    "dot",
    "box",
    "violin",
    "scatter",
    "line",
    "hist",
]


def test_base_theme_is_complete() -> None:
    missing = [f for f in STYLE_FIELDS if getattr(BASE_THEME, f) is None]
    assert missing == []


@pytest.mark.parametrize("preset", presets.list())
@pytest.mark.parametrize("theme", list_themes())
def test_every_preset_theme_and_plot_kind_resolves(preset: str, theme: str) -> None:
    for kind in PLOT_KINDS:
        style = resolve(kind, preset=presets.get(preset), theme=get_theme(theme))
        assert all(getattr(style.theme, f) is not None for f in STYLE_FIELDS)
        assert style.width > 0
        assert style.height > 0


def test_first_layer_wins_and_provenance_is_recorded() -> None:
    result = cascade([Layer("top", Theme(font_size=12)), Layer("base", BASE_THEME)])
    assert result.theme.font_size == 12
    assert result.provenance["font_size"] == "top"
    assert result.provenance["grid"] == "base"


def test_roles_derive_from_a_higher_layer_palette() -> None:
    result = cascade(
        [
            Layer("preset", Theme(palette=("#0f5499", "#eb5e8d"))),
            Layer("base", BASE_THEME),
        ]
    )
    assert result.theme.primary == "#0f5499"
    assert result.theme.highlight == "#0f5499"
    assert result.theme.sequential is not None
    assert result.theme.sequential[1] == "#0f5499"
    assert "derived from palette of preset" in result.provenance["sequential"]


def test_explicit_role_in_same_layer_beats_derivation() -> None:
    result = cascade(
        [
            Layer("preset", Theme(palette=("#111111",), primary="#222222")),
            Layer("base", BASE_THEME),
        ]
    )
    assert result.theme.primary == "#222222"


def test_journal_text_fits_range_and_keeps_hierarchy() -> None:
    style = resolve("bar", preset=presets.get("nature"), theme=BASE_THEME)
    sizes = style.sizes
    assert 5 <= sizes.tick <= sizes.label <= sizes.title <= 7
    assert sizes.panel == 8
    assert style.adjustments  # recorded, but silent for library defaults


def test_explicit_font_size_adjustment_warns() -> None:
    with pytest.warns(sp.ConstraintAdjustedWarning, match="font_size=12"):
        resolve(
            "bar",
            preset=presets.get("nature"),
            theme=BASE_THEME,
            overrides=Theme(font_size=12),
        )


def test_strict_mode_raises() -> None:
    sp.config.strict = True
    with pytest.raises(sp.ConstraintAdjustedWarning):
        resolve(
            "bar",
            preset=presets.get("nature"),
            theme=BASE_THEME,
            overrides=Theme(font_size=12),
        )


def test_min_line_width_enforced() -> None:
    style = resolve("bar", preset=presets.get("poster"), theme=BASE_THEME)
    assert style.theme.axis_line_width == 2
    assert style.theme.grid_width == 2


def test_height_clamped_to_max() -> None:
    with pytest.warns(sp.ConstraintAdjustedWarning, match="maximum"):
        style = resolve(
            "bar", preset=presets.get("nature"), theme=BASE_THEME, height="300mm"
        )
    assert style.height == pytest.approx(170 / 25.4)


def test_rc_embeds_truetype_fonts() -> None:
    rc = resolve("bar", preset=presets.get("nature"), theme=BASE_THEME).rc()
    assert rc["pdf.fonttype"] == 42
    assert rc["ps.fonttype"] == 42


def test_explain_reports_layer() -> None:
    plot = sp.bar([1, 2]).theme(grid="none")
    assert plot.explain("grid") == f"grid = 'none'  [{PLOT_LAYER}]"
    with pytest.raises(KeyError):
        plot.explain("nonsense")
