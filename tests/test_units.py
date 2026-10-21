import pytest

from SecretPlots.core.units import to_inches


@pytest.mark.parametrize(
    ("value", "inches"),
    [
        (3.5, 3.5),
        ("89mm", 89 / 25.4),
        ("8.9 cm", 89 / 25.4),
        ("2in", 2.0),
        ("72pt", 1.0),
        ("600px", 6.0),
    ],
)
def test_to_inches(value: float | str, inches: float) -> None:
    assert to_inches(value) == pytest.approx(inches)


def test_px_uses_px_per_inch() -> None:
    assert to_inches("640px", px_per_inch=72) == pytest.approx(640 / 72)


@pytest.mark.parametrize("bad", ["", "wide", "12 furlongs", "-3mm", 0, -1, True])
def test_rejects_bad_lengths(bad: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        to_inches(bad)  # type: ignore[arg-type]
