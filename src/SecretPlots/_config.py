from dataclasses import dataclass


@dataclass
class Config:
    """Library-wide switches, exposed as ``SecretPlots.config``.

    Attributes:
        strict: Raise :class:`SecretPlotsWarning` subclasses as errors instead of
            warning. Useful when checking figures in CI before submission.
        enforce_limits: Apply a preset's limits (font sizes, line widths, maximum
            height, required font family) even to values you set explicitly on
            a plot. By default your explicit values are kept and a
            :class:`LimitExceededWarning` says which limits they break.
    """

    strict: bool = False
    enforce_limits: bool = False


config = Config()
