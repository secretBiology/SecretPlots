"""Active preset/theme selection (``sp.use``).

A plain module-level stack rather than a ContextVar: Jupyter runs each cell in a
fresh context copy, so a ContextVar set in one cell would vanish in the next.
"""

from dataclasses import dataclass, replace
from types import TracebackType

from SecretPlots import presets
from SecretPlots.core.units import Length
from SecretPlots.theme import Theme, get_theme


@dataclass(frozen=True)
class Selection:
    preset: str = presets.DEFAULT
    theme: Theme | str = "secret"
    width: Length | None = None

    def preset_obj(self) -> presets.Preset:
        return presets.get(self.preset)

    def theme_obj(self) -> Theme:
        return self.theme if isinstance(self.theme, Theme) else get_theme(self.theme)


_stack: list[Selection] = [Selection()]


def current() -> Selection:
    return _stack[-1]


class use:  # noqa: N801  (used like a function: sp.use(...) / with sp.use(...))
    """Select the active preset and/or theme.

    Call it to change the default for the rest of the session, or use it as a
    context manager to change it temporarily::

        sp.use(preset="nature")
        with sp.use(theme="dark", preset="web", width="mobile"):
            ...
    """

    def __init__(
        self,
        preset: str | None = None,
        *,
        theme: Theme | str | None = None,
        width: Length | None = None,
    ) -> None:
        if preset is not None:
            presets.get(preset)  # fail fast on typos
        if isinstance(theme, str):
            get_theme(theme)
        previous = current()
        changes: dict[str, object] = {}
        if preset is not None:
            changes["preset"] = preset
            changes["width"] = width  # widths are preset-specific
        elif width is not None:
            changes["width"] = width
        if theme is not None:
            changes["theme"] = theme
        self._selection = replace(previous, **changes)  # type: ignore[arg-type]
        self._depth = len(_stack)
        _stack.append(self._selection)

    def __enter__(self) -> Selection:
        return self._selection

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        del _stack[self._depth :]


def reset() -> None:
    """Return to the default preset and theme."""
    del _stack[1:]
