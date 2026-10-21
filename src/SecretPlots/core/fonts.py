"""Font fallback resolution.

Each style layer may name a font chain (most preferred first). We resolve the
chain ourselves against installed fonts and hand matplotlib one concrete family,
which avoids matplotlib's repeated "findfont: Font family not found" messages.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache

from matplotlib import font_manager

from SecretPlots.errors import FontFallbackWarning, emit

#: Shipped with matplotlib, so always available.
LAST_RESORT = {
    "sans-serif": "DejaVu Sans",
    "serif": "DejaVu Serif",
    "monospace": "DejaVu Sans Mono",
}

#: Common fonts of each generic family, used when a plot sets only ``font_generic``.
GENERIC_FAMILIES: dict[str, tuple[str, ...]] = {
    "sans-serif": ("Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"),
    "serif": ("Times New Roman", "Times", "Georgia", "DejaVu Serif"),
    "monospace": ("Menlo", "Consolas", "Courier New", "DejaVu Sans Mono"),
}


@dataclass(frozen=True)
class FontChain:
    source: str
    families: tuple[str, ...]
    generic: str | None
    #: Set explicitly by the user: used even if it conflicts with the preset.
    forced: bool = False


@dataclass(frozen=True)
class FontChoice:
    family: str
    source: str
    preferred: tuple[str, ...]
    is_fallback: bool


@cache
def _installed() -> dict[str, str]:
    return {f.name.casefold(): f.name for f in font_manager.fontManager.ttflist}


def installed_name(family: str) -> str | None:
    """Installed spelling of ``family`` (case-insensitive), or ``None``."""
    return _installed().get(family.casefold())


def refresh() -> None:
    """Re-scan installed fonts (call after installing fonts mid-session)."""
    _installed.cache_clear()


def resolve_font(
    chains: Sequence[FontChain], *, required_generic: str | None
) -> FontChoice:
    """Pick the first installed font, walking chains in priority order.

    Chains whose generic family conflicts with ``required_generic`` (e.g. a serif
    theme under a sans-serif-only journal) are skipped unless ``forced``. Warns
    once per session when nothing from the highest-priority chain is installed.
    """
    usable = [
        c
        for c in chains
        if c.forced or required_generic is None or c.generic in (None, required_generic)
    ]
    preferred = usable[0] if usable else None

    choice: FontChoice | None = None
    for chain in usable:
        for family in chain.families:
            name = installed_name(family)
            if name is not None:
                choice = FontChoice(
                    family=name,
                    source=chain.source,
                    preferred=preferred.families if preferred else (),
                    is_fallback=chain is not preferred,
                )
                break
        if choice is not None:
            break

    if choice is None:
        generic = required_generic or (preferred.generic if preferred else None)
        choice = FontChoice(
            family=LAST_RESORT.get(generic or "sans-serif", "DejaVu Sans"),
            source="matplotlib default",
            preferred=preferred.families if preferred else (),
            is_fallback=True,
        )

    if choice.is_fallback and preferred is not None:
        emit(
            FontFallbackWarning,
            f"None of the fonts preferred by {preferred.source} are installed "
            f"({', '.join(preferred.families)}); using {choice.family!r} from "
            f"{choice.source}. Install {preferred.families[0]!r} for the intended "
            "look, then call SecretPlots.fonts.refresh().",
            once_key=preferred.source + "|" + ",".join(preferred.families),
            stacklevel=5,
        )
    return choice


def status(families: Sequence[str]) -> dict[str, bool]:
    """Which of ``families`` are installed."""
    return {f: installed_name(f) is not None for f in families}
