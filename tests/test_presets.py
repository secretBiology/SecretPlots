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
    assert presets.list(kind="journal") == sorted(
        [
            "aha",
            "cell",
            "nature",
            "pnas",
            "science",
            "ieee",
            "acm",
            "elsevier",
            "springer",
            "neurips",
        ]
    )


MM = 1 / 25.4


@pytest.mark.parametrize(
    ("name", "widths", "font_range", "panel_size"),
    [
        ("science", {"single": 90, "double": 183}, (6, 9), 10),
        ("cell", {"single": 85, "one-and-half": 114, "double": 174}, (6, 8), None),
        ("pnas", {"single": 87, "one-and-half": 114, "double": 178}, (6, None), None),
        ("aha", {"single": 80, "one-and-half": 127.5, "double": 177.5}, (6, 10), 12.6),
        ("ieee", {"single": 88.9, "double": 181.864}, (None, None), None),
        ("acm", {"single": 240 / 72 * 25.4, "double": 7 * 25.4}, (None, None), None),
        (
            "elsevier",
            {"single": 90, "one-and-half": 140, "double": 190},
            (6, None),
            None,
        ),
        ("springer", {"single": 84, "double": 174, "small": 119}, (8, 12), None),
        ("neurips", {"full": 5.5 * 25.4}, (None, None), None),
    ],
)
def test_journal_specs(
    name: str,
    widths: dict[str, float],
    font_range: tuple[float, float | None],
    panel_size: float | None,
) -> None:
    preset = presets.get(name)
    assert preset.official
    assert preset.source_url
    for key, mm in widths.items():
        assert preset.target.widths[key] == pytest.approx(mm * MM)
    target = preset.target
    assert (target.min_font_size, target.max_font_size) == font_range
    assert preset.chrome.panel_label_size == panel_size


@pytest.mark.parametrize(
    "name",
    [
        "science",
        "cell",
        "pnas",
        "aha",
        "ieee",
        "acm",
        "elsevier",
        "springer",
        "neurips",
    ],
)
def test_journal_text_fits_without_clamping(name: str) -> None:
    style = sp.bar([1]).preset(name).style()
    target = style.preset.target
    sizes = [style.sizes.tick, style.sizes.label, style.sizes.title, style.sizes.note]
    assert min(sizes) >= (target.min_font_size or 0)
    assert max(sizes) <= (target.max_font_size or float("inf"))
    assert not [a for a in style.adjustments if "text" in a]


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
