"""Font availability for themes and presets.

>>> import SecretPlots as sp
>>> sp.fonts.status("nyt-like")          # doctest: +SKIP
{'Libre Franklin': False, 'Franklin Gothic Medium': False, ..., 'Arial': True}
"""

from SecretPlots import presets
from SecretPlots.core.fonts import refresh
from SecretPlots.theme import BASE_THEME, get_theme, list_themes

__all__ = ["refresh", "status"]


def status(name: str = BASE_THEME.name) -> dict[str, bool]:
    """Installed/missing fonts preferred by a preset or theme, in order."""
    from SecretPlots.core.fonts import status as _status

    if name in list_themes():
        families = get_theme(name).font_family or BASE_THEME.font_family or ()
    else:
        families = presets.get(name).theme.font_family or BASE_THEME.font_family or ()
    return _status(families)
