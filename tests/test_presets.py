from pathlib import Path

import pytest

import SecretPlots as sp
from SecretPlots import presets


def test_builtin_presets_load() -> None:
    names = presets.list()
    for expected in (
        "nature",
        "bbc",
        "nyt-like",
        "wapo-like",
        "ft-like",
        "economist-like",
        "screen",
    ):
        assert expected in names
    assert presets.list(kind="journal") == ["nature"]


def test_nature_spec() -> None:
    nature = presets.get("nature")
    assert nature.official
    assert nature.target.widths["single"] == pytest.approx(89 / 25.4)
    assert nature.target.widths["double"] == pytest.approx(183 / 25.4)
    assert nature.target.max_height == pytest.approx(170 / 25.4)
    assert (nature.target.min_font_size, nature.target.max_font_size) == (5, 7)
    assert nature.chrome.panel_label_size == 8


def test_bbc_canvas_matches_bbplot() -> None:
    target = presets.get("bbc").target
    assert target.width() * target.px_per_inch == pytest.approx(640)
    assert target.width() * target.aspect * target.px_per_inch == pytest.approx(450)


def test_unofficial_news_presets_carry_disclaimer() -> None:
    for name in presets.list(kind="news"):
        preset = presets.get(name)
        if not preset.official:
            assert name.endswith("-like")
            assert preset.disclaimer
            assert "Not affiliated" in preset.disclaimer


def test_unknown_preset_suggests_close_match() -> None:
    with pytest.raises(sp.PresetNotFoundError, match="Did you mean 'nature'"):
        presets.get("natrue")


def test_unknown_width_lists_options() -> None:
    with pytest.raises(sp.PresetError, match="double"):
        presets.get("nature").target.width("triple")


def test_explicit_width_allowed() -> None:
    assert presets.get("nature").target.width("120mm") == pytest.approx(120 / 25.4)


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "custom.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_register_from_toml(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        'name = "lab"\nkind = "generic"\n[target]\nwidths = { slide = "10in" }\n'
        '[theme]\npalette = ["#000000", "#ff0000"]\n',
    )
    preset = presets.register(path)
    assert presets.get("lab") is preset
    assert preset.theme.palette == ("#000000", "#ff0000")
    with pytest.raises(sp.PresetError, match="exists"):
        presets.register(path)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            'name = "x"\nkind = "generic"\ncolour = 1\n[target]\nwidths = { a = "1in" }\n',
            "unknown key",
        ),
        (
            'name = "x"\nkind = "generic"\n[target]\nwidths = { a = "1in" }\n[theme]\npallete = []\n',
            "pallete",
        ),
        (
            'name = "x"\nkind = "magazine"\n[target]\nwidths = { a = "1in" }\n',
            "magazine",
        ),
        (
            'name = "x"\nkind = "generic"\n[target]\nwidths = { a = "wide" }\n',
            "Cannot parse",
        ),
        (
            'name = "x"\nkind = "generic"\n[target]\nwidths = { a = "1in" }\n[theme]\ngrid = "diagonal"\n',
            "diagonal",
        ),
        ('name = "x"\nkind = "generic"\n', "target"),
    ],
)
def test_strict_validation(tmp_path: Path, body: str, message: str) -> None:
    with pytest.raises(sp.PresetError, match=message):
        presets.load(_write(tmp_path, body))
