"""Color helpers: palette extension, derived colormaps, readable text."""

from collections.abc import Sequence

from matplotlib.colors import Colormap, LinearSegmentedColormap, to_hex
from SecretColors.utils import mix, text_color

from SecretPlots.errors import PaletteExtendedWarning, emit

#: Beyond this many categories, color alone stops being a useful encoding.
MANY_CATEGORIES = 8


def _mix(a: str, b: str, ratio: float) -> str:
    return to_hex(str(mix(a, b, ratio)))


def extend_palette(
    palette: Sequence[str], n: int, *, background: str, source: str = "palette"
) -> list[str]:
    """Return ``n`` colors. Never cycles: when the palette is too short, tints
    and shades of the palette's own colors are added so the look is kept."""
    base = [to_hex(c) for c in palette]
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


def colormap(stops: Sequence[str], name: str = "secretplots") -> Colormap:
    """Matplotlib colormap from color stops, or a named matplotlib colormap."""
    if len(stops) == 1:
        import matplotlib as mpl

        return mpl.colormaps[stops[0]]
    return LinearSegmentedColormap.from_list(name, list(stops))


def readable_on(background: str, *, dark: str, light: str) -> str:
    """``dark`` or ``light`` text, whichever reads better on ``background``."""
    return light if str(text_color(to_hex(background))).lower() == "#ffffff" else dark
