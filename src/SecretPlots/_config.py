from dataclasses import dataclass


@dataclass
class Config:
    """Library-wide switches, exposed as ``SecretPlots.config``.

    Attributes:
        strict: Raise :class:`SecretPlotsWarning` subclasses as errors instead of
            warning. Useful when checking figures in CI before submission.
    """

    strict: bool = False


config = Config()
