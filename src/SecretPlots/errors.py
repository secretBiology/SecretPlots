"""Exceptions and warnings raised by SecretPlots.

Every warning subclasses :class:`SecretPlotsWarning`, so all of them can be
filtered at once::

    import warnings
    warnings.filterwarnings("ignore", category=SecretPlots.SecretPlotsWarning)
"""

import warnings

from SecretPlots._config import config


class SecretPlotsError(Exception):
    """Base class for all SecretPlots errors."""


class PresetNotFoundError(SecretPlotsError, KeyError):
    """Requested preset or theme name is not registered."""

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


class PresetError(SecretPlotsError, ValueError):
    """A preset definition is invalid (unknown keys, bad values)."""


class DataShapeError(SecretPlotsError, ValueError):
    """Input data cannot be interpreted for the requested plot."""


class SecretPlotsWarning(UserWarning):
    """Base class for all SecretPlots warnings."""


class FontFallbackWarning(SecretPlotsWarning):
    """None of the preferred fonts are installed; a fallback font was used."""


class PaletteExtendedWarning(SecretPlotsWarning):
    """More categories than palette colors; extra shades were generated."""


class ConstraintAdjustedWarning(SecretPlotsWarning):
    """A value you set explicitly was changed to satisfy the target's limits."""


class LimitExceededWarning(SecretPlotsWarning):
    """A value you set explicitly breaks the preset's limits and was kept anyway.

    Set ``SecretPlots.config.enforce_limits = True`` to apply the limits instead.
    """


class LabelsHiddenWarning(SecretPlotsWarning):
    """Some labels did not fit: they were hidden, or may overlap."""


class ColormapWarning(SecretPlotsWarning):
    """The colormap misleads (rainbow) or is not colour-blind safe (red-green)."""


class SmallSampleWarning(SecretPlotsWarning):
    """Too few values for the plot to describe the data reliably."""


class FormatWarning(SecretPlotsWarning):
    """File format is not one the preset's publisher accepts."""


class PolicyWarning(SecretPlotsWarning):
    """SecretPlots applied a deliberate rule that changes what you asked for.

    The message names the rule, why it exists, and how to opt out.
    """


_already_warned: set[tuple[type[Warning], str]] = set()


def emit(
    category: type[SecretPlotsWarning],
    message: str,
    *,
    once_key: str | None = None,
    stacklevel: int = 3,
) -> None:
    """Warn (or raise in strict mode), optionally only once per session.

    Strict mode is checked first: a warning seen earlier in the session must
    still fail every later strict call.
    """
    if config.strict:
        raise category(message)
    if once_key is not None:
        key = (category, once_key)
        if key in _already_warned:
            return
        _already_warned.add(key)
    warnings.warn(message, category, stacklevel=stacklevel)


def reset_once_warnings() -> None:
    """Forget which once-per-session warnings were already shown."""
    _already_warned.clear()
