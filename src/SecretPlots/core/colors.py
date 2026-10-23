"""Color helpers: palette extension, colormaps, readable text."""

import difflib
from collections.abc import Sequence
from typing import Any

import matplotlib as mpl
import pandas as pd
from matplotlib.colors import Colormap, LinearSegmentedColormap, to_hex, to_rgba
from SecretColors import cmaps as sc_cmaps
from SecretColors.cmaps.maps import _SPECIAL as _SC_SPECIAL
from SecretColors.utils import mix, text_color

from SecretPlots.errors import ColormapWarning, PaletteExtendedWarning, emit

#: Beyond this many categories, color alone stops being a useful encoding.
MANY_CATEGORIES = 8


def _mix(a: str, b: str, ratio: float) -> str:
    return to_hex(str(mix(a, b, ratio)))


def with_alpha(color: str, alpha: float | None) -> str:
    """``color`` made ``alpha`` times as opaque (``None`` leaves it alone)."""
    if alpha is None:
        return color
    r, g, b, a = to_rgba(color)
    return to_hex((r, g, b, a * alpha), keep_alpha=True)


def darken(color: str, amount: float) -> str:
    """``color`` mixed with black (``amount`` 0 to 1), keeping its alpha."""
    alpha = to_rgba(color)[3]
    return with_alpha(_mix(to_hex(color), "#000000", amount), alpha)


def combined_alpha(color: Any, alpha: float | None) -> float | None:
    """Artist ``alpha`` that keeps the color's own alpha: matplotlib's
    ``alpha=`` replaces it instead of multiplying."""
    own = to_rgba(color)[3]
    if alpha is None:
        return None if own == 1 else own
    return alpha * own


def extend_palette(
    palette: Sequence[str], n: int, *, background: str, source: str = "palette"
) -> list[str]:
    """Return ``n`` colors. Never cycles: when the palette is too short, tints
    and shades of the palette's own colors are added so the look is kept."""
    # Alpha written into a color ("#ff000080") is kept, so it can combine
    # with the theme's opacity instead of being silently dropped.
    base = [to_hex(c, keep_alpha=to_rgba(c)[3] < 1) for c in palette]
    if n <= len(base):
        return base[:n]

    extra: list[str] = []
    for ratio, toward in ((0.45, background), (0.35, "#000000"), (0.7, background)):
        for color in base:
            candidate = _mix(color, toward, ratio)
            if candidate not in base and candidate not in extra:
                extra.append(candidate)
    colors = (base + extra)[:n]
    if len(colors) < n:
        raise ValueError(f"Cannot build {n} distinct colors from {source}")

    hint = (
        " With this many categories consider .highlight(...) or grouping small "
        "ones into 'Other'."
        if n > MANY_CATEGORIES
        else ""
    )
    emit(
        PaletteExtendedWarning,
        f"{n} categories but {source} has {len(base)} colors; generated "
        f"{n - len(base)} extra shades instead of repeating colors.{hint}",
        stacklevel=5,
    )
    return colors


def derived_sequential(primary: str, background: str) -> tuple[str, ...]:
    return (
        _mix(primary, background, 0.88),
        to_hex(primary),
        _mix(primary, "#000000", 0.5),
    )


def derived_diverging(negative: str, positive: str, background: str) -> tuple[str, ...]:
    return (to_hex(negative), _mix(background, "#808080", 0.12), to_hex(positive))


#: Colormaps that mislead (uneven lightness) or that readers with red-green
#: colour blindness cannot read. Nature's figure guide and Crameri et al. 2020
#: (Nat Commun 11:5444) both ask authors to avoid them.
_RAINBOW = {
    "jet",
    "rainbow",
    "turbo",
    "hsv",
    "gist_rainbow",
    "nipy_spectral",
    "gist_ncar",
    "spectral",
    "cyclic",
}
_RED_GREEN = {
    "rdylgn",
    "redgreen",
    "redgreen_light",
    "arearedgreen",
    "redwhitegreen",
    "redwhitegreen_light",
    "trafficlight",
}

_SC_KINDS = {
    "seq": "sequential",
    "div": "diverging",
    "qual": "qualitative",
    "regular": "qualitative",
}


def _kind(name: str) -> str:
    data = _SC_SPECIAL.get(name)
    return "sequential" if data is None else _SC_KINDS.get(data[1].get("type"), "?")


def colormaps(kind: str | None = None) -> pd.DataFrame:
    """Colormaps you can pass by name to ``.cmap()`` (from SecretColors).

    Any matplotlib colormap name (e.g. ``"viridis"``) works too, as does a
    SecretColors palette color name (``"teal"``) for a single-hue ramp.

    Args:
        kind: ``"sequential"``, ``"diverging"`` or ``"qualitative"`` to filter.
    """
    rows = []
    for source in ("standard", "brewer", "tableau", "colorblind"):
        for name in sc_cmaps.available(source):
            key = name.lower()
            note = ""
            if key in _RAINBOW:
                note = "rainbow-like; avoid for data"
            elif key in _RED_GREEN:
                note = "red-green; not colour-blind safe"
            rows.append(
                {"name": name, "kind": _kind(name), "source": source, "note": note}
            )
    table = pd.DataFrame(rows)
    if kind is not None:
        kinds = ("sequential", "diverging", "qualitative")
        if kind not in kinds:
            raise ValueError(f"kind must be one of {kinds}")
        table = table[table["kind"] == kind]
    return table.set_index("name")


def _check_cmap_name(name: str) -> None:
    key = name.lower().removeprefix("sc.").removesuffix("_r")
    if key in _RAINBOW:
        problem = "is a rainbow map: uneven lightness creates false boundaries"
    elif key in _RED_GREEN:
        problem = "mixes red and green, which colour-blind readers cannot tell apart"
    else:
        return
    emit(
        ColormapWarning,
        f"Colormap {name!r} {problem}. Journals (e.g. Nature) ask authors to "
        "avoid it. Use a sequential map such as 'blues' or 'viridis', or a "
        "diverging one such as 'RdBu' or 'tol_sunset'; sp.colormaps() lists them.",
        once_key=key,
        stacklevel=6,
    )


def resolve_cmap(spec: Any, *, reverse: bool = False) -> Colormap:
    """Matplotlib colormap from a SecretColors name (``"blues"``, ``"RdBu"``,
    ``"tol_sunset"``, ``"sc.teal"``), a matplotlib name (``"viridis"``), a
    list of colour stops (low to high) or a ``Colormap``."""
    if isinstance(spec, Colormap):
        cmap = spec
    elif isinstance(spec, str):
        _check_cmap_name(spec)
        name = spec.removeprefix("sc.")
        flipped = name.endswith("_r")
        if flipped:
            name = name[:-2]
        try:
            cmap = sc_cmaps.cmap(name, reverse=flipped)
        except ValueError:
            if spec in mpl.colormaps:
                cmap = mpl.colormaps[spec]
            else:
                options = [*sc_cmaps.available(), *mpl.colormaps]
                close = difflib.get_close_matches(spec, options, n=3)
                hint = f" Did you mean {close}?" if close else ""
                raise ValueError(
                    f"Unknown colormap {spec!r}.{hint} sp.colormaps() lists the "
                    "SecretColors maps; matplotlib names like 'viridis' work too."
                ) from None
    else:
        items = list(spec)
        if len(items) == 1 and isinstance(items[0], str):
            return resolve_cmap(items[0], reverse=reverse)
        if len(items) < 2:
            raise ValueError("A colormap needs a name or at least 2 colors")
        stops = [to_hex(c) for c in items]
        cmap = LinearSegmentedColormap.from_list("secretplots", stops)
    return cmap.reversed() if reverse else cmap


def readable_on(background: str, *, dark: str, light: str) -> str:
    """``dark`` or ``light`` text, whichever reads better on ``background``."""
    return light if str(text_color(to_hex(background))).lower() == "#ffffff" else dark
