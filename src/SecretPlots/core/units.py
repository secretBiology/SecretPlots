"""Length parsing. Internally every length is in inches."""

import re

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0
#: Default pixels per inch for ``"px"`` lengths. Matches matplotlib's default
#: dpi, so a 600px-wide target saved at dpi=100 is exactly 600 pixels wide.
DEFAULT_PX_PER_INCH = 100.0

Length = float | int | str

_LENGTH = re.compile(r"^\s*(?P<num>[0-9]*\.?[0-9]+)\s*(?P<unit>mm|cm|in|pt|px)?\s*$")
_FACTORS = {
    "in": 1.0,
    "mm": 1 / MM_PER_INCH,
    "cm": 10 / MM_PER_INCH,
    "pt": 1 / PT_PER_INCH,
}


def to_inches(value: Length, *, px_per_inch: float = DEFAULT_PX_PER_INCH) -> float:
    """Convert ``3.5``, ``"89mm"``, ``"8.9cm"``, ``"3.5in"``, ``"12pt"`` or
    ``"600px"`` to inches. Bare numbers are inches.

    >>> round(to_inches("89mm"), 3)
    3.504
    """
    if isinstance(value, bool):
        raise TypeError("Length cannot be a bool")
    if isinstance(value, int | float):
        if value <= 0:
            raise ValueError(f"Length must be positive, got {value}")
        return float(value)
    match = _LENGTH.match(value)
    if match is None:
        raise ValueError(
            f"Cannot parse length {value!r}. Use a number (inches) or a string "
            "like '89mm', '8.9cm', '3.5in', '12pt' or '600px'."
        )
    number = float(match["num"])
    if number <= 0:
        raise ValueError(f"Length must be positive, got {value!r}")
    unit = match["unit"] or "in"
    if unit == "px":
        return number / px_per_inch
    return number * _FACTORS[unit]
