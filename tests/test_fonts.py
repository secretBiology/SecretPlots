import pytest

import SecretPlots as sp
from SecretPlots import presets
from SecretPlots.core.fonts import FontChain, resolve_font
from SecretPlots.core.resolve import resolve
from SecretPlots.theme import BASE_THEME, Theme


@pytest.mark.usefixtures("only_dejavu")
def test_falls_back_to_dejavu_and_warns_once() -> None:
    with pytest.warns(sp.FontFallbackWarning, match="Libre Franklin"):
        style = resolve("bar", preset=presets.get("nyt-like"), theme=BASE_THEME)
    assert style.font.family == "DejaVu Sans"
    assert style.font.is_fallback

    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        resolve(
            "bar", preset=presets.get("nyt-like"), theme=BASE_THEME
        )  # no second warning


@pytest.mark.usefixtures("only_dejavu")
def test_later_font_in_same_chain_is_not_a_fallback() -> None:
    choice = resolve_font(
        [FontChain("preset", ("Nope Sans", "DejaVu Sans"), "sans-serif")],
        required_generic=None,
    )
    assert choice.family == "DejaVu Sans"
    assert not choice.is_fallback


@pytest.mark.usefixtures("only_dejavu")
def test_serif_chain_skipped_when_sans_required() -> None:
    choice = resolve_font(
        [
            FontChain("plot", ("DejaVu Serif",), "serif"),
            FontChain("base", ("DejaVu Sans",), "sans-serif"),
        ],
        required_generic="sans-serif",
    )
    assert choice.family == "DejaVu Sans"


@pytest.mark.usefixtures("only_dejavu")
def test_serif_theme_allowed_without_constraint() -> None:
    style = resolve(
        "bar",
        preset=presets.get("screen"),
        theme=BASE_THEME,
        overrides=Theme(font_family=("DejaVu Serif",), font_generic="serif"),
    )
    assert style.font.family == "DejaVu Serif"


def test_status_reports_installed_fonts() -> None:
    status = sp.fonts.status("nyt-like")
    assert next(iter(status)) == "Libre Franklin"
    assert all(isinstance(v, bool) for v in status.values())
