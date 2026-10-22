import pytest

import SecretPlots as sp
from SecretPlots import presets
from SecretPlots.core.merge import Layer, cascade
from SecretPlots.core.resolve import PLOT_LAYER, Style, resolve
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


def _nature(**overrides: object) -> Style:
    return resolve(
        "bar",
        preset=presets.get("nature"),
        theme=BASE_THEME,
        overrides=Theme(**overrides),  # type: ignore[arg-type]
    )


def test_explicit_font_size_is_kept_with_warning() -> None:
    with pytest.warns(sp.LimitExceededWarning, match=r"font_size=12 .*enforce_limits"):
        style = _nature(font_size=12)
    assert style.sizes.tick == 12
    assert any("kept your font_size=12" in a for a in style.adjustments)


def test_enforce_limits_clamps_explicit_font_size() -> None:
    sp.config.enforce_limits = True
    with pytest.warns(sp.ConstraintAdjustedWarning, match="font_size=12"):
        style = _nature(font_size=12)
    assert style.sizes.title <= 7


def test_strict_mode_raises() -> None:
    sp.config.strict = True
    with pytest.raises(sp.LimitExceededWarning):
        _nature(font_size=12)


def test_explicit_line_width_below_minimum_is_kept() -> None:
    with pytest.warns(sp.LimitExceededWarning, match="grid_width"):
        style = resolve(
            "bar",
            preset=presets.get("poster"),
            theme=BASE_THEME,
            overrides=Theme(grid_width=0.5),
        )
    assert style.theme.grid_width == 0.5
    assert style.theme.axis_line_width == 2  # not set by you: still raised


def test_min_line_width_enforced() -> None:
    style = resolve("bar", preset=presets.get("poster"), theme=BASE_THEME)
    assert style.theme.axis_line_width == 2
    assert style.theme.grid_width == 2


def test_explicit_height_above_max_is_kept() -> None:
    with pytest.warns(sp.LimitExceededWarning, match="height"):
        style = resolve(
            "bar", preset=presets.get("nature"), theme=BASE_THEME, height="300mm"
        )
    assert style.height == pytest.approx(300 / 25.4)


def test_enforce_limits_clamps_height() -> None:
    sp.config.enforce_limits = True
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


def test_text_keeps_point_size_by_default() -> None:
    small = sp.bar([1]).size("4in").style().sizes
    large = sp.bar([1]).size("9in").style().sizes
    assert small == large


def test_scale_text_grows_with_width() -> None:
    style = sp.bar([1]).size("wide", scale_text=True).style()  # 9 in vs 6 in default
    assert style.sizes.tick == pytest.approx(9.0 * 1.5)
    assert any("scale_text" in a for a in style.adjustments)
    shrunk = sp.bar([1]).size("3in", scale_text=True).style()
    assert shrunk.sizes.tick == pytest.approx(9.0 * 0.5)


def test_scale_text_may_exceed_journal_limits() -> None:
    plot = sp.bar([1]).preset("nature", width="double").size(scale_text=True)
    with pytest.warns(sp.LimitExceededWarning, match="scale_text"):
        sizes = plot.style().sizes
    assert sizes.tick == pytest.approx(9.0 * 183 / 89, abs=0.01)


def test_scale_text_obeys_journal_limits_when_enforced() -> None:
    sp.config.enforce_limits = True
    plot = sp.bar([1]).preset("nature", width="double").size(scale_text=True)
    with pytest.warns(sp.ConstraintAdjustedWarning, match="scale_text"):
        sizes = plot.style().sizes
    assert sizes.title <= 7


def test_scale_text_can_be_turned_off_again() -> None:
    plot = sp.bar([1]).size("wide", scale_text=True).size(scale_text=False)
    assert plot.style().sizes.tick == 9.0


def test_theme_overrides_are_validated() -> None:
    with pytest.raises(sp.PresetError, match="diagonal"):
        sp.bar([1]).theme(grid="diagonal")
    with pytest.raises(sp.PresetError, match="number"):
        sp.bar([1]).theme(font_size="big")
    with pytest.raises(TypeError, match="theme_options"):
        sp.bar([1]).theme(fontsize=12)
    plot = sp.bar([1]).theme(spines=["left"], font_size=12)
    assert plot.style().theme.spines == ("left",)
    assert plot.style().theme.font_size == 12.0


def test_aspect_sets_plot_area_shape() -> None:
    def shape(plot: sp.Plot) -> float:
        box = plot.ax.get_window_extent(plot.fig.canvas.get_renderer())
        return box.height / box.width

    data = list(range(50))
    assert shape(sp.histogram(data).size(6, 3).theme(aspect=1)) == pytest.approx(1)
    assert shape(sp.histogram(data).size(4, 4).theme(aspect=0.5)) == pytest.approx(0.5)
    assert shape(sp.histogram(data).size(6, 3)) < 0.6  # "auto" fills the figure
    with pytest.raises(sp.PresetError, match="more than 0"):
        sp.bar([1]).theme(aspect=0)
    with pytest.raises(sp.PresetError):
        sp.bar([1]).theme(aspect="square")


def test_theme_options_lists_every_field_with_docs() -> None:
    table = sp.theme_options()
    assert list(table.index) == list(STYLE_FIELDS)
    assert table["description"].map(bool).all()
    assert "'value'" in table.loc["grid", "allowed"]
    assert table.loc["font_size", "value"] == 9.0
    dark = sp.theme_options("dark")
    assert dark.loc["font_size", "value"] is None  # inherited
