"""Visual regression baselines. Regenerate with:
uv run pytest tests/test_images.py --mpl-generate-path=tests/baseline
"""

import pandas as pd
import pytest
from matplotlib.figure import Figure

import SecretPlots as sp

pytestmark = pytest.mark.usefixtures("only_dejavu")
TOLERANCE = 3


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_bar_default(expression: pd.DataFrame) -> Figure:
    return (
        sp.bar(expression, x="gene", y="tpm", hue="sample", error="sd")
        .values(".1f")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_bar_nature_single(expression: pd.DataFrame) -> Figure:
    return (
        sp.bar(expression, x="gene", y="tpm", hue="sample", error="sem")
        .preset("nature")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_bar_nature_double_horizontal(expression: pd.DataFrame) -> Figure:
    return (
        sp.bar(expression, x="gene", y="tpm", orient="h", sort="desc")
        .preset("nature", width="double")
        .values(".1f")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_bar_ft_like_chrome(expression: pd.DataFrame) -> Figure:
    return (
        sp.bar(expression, x="gene", y="tpm", hue="sample")
        .chrome(title="Cardiac genes", subtitle="Mean TPM", source="Example data")
        .preset("ft-like")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_bar_economist_like_highlight() -> Figure:
    return (
        sp.bar({"2021": 3, "2022": 5, "2023": 4, "2024": 7})
        .highlight("2024")
        .chrome(title="A record year", source="Example data")
        .preset("economist-like")
        .fig
    )
