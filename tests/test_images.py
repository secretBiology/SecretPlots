"""Visual regression baselines. Regenerate with:
uv run pytest tests/test_images.py --mpl-generate-path=tests/baseline
"""

import numpy as np
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


@pytest.fixture
def expression_matrix() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    values = rng.normal(5, 0.8, (12, 6))
    values[:6, 3:] += 2.5
    values[8:, :3] += 1.5
    frame = pd.DataFrame(
        values,
        index=pd.Index([f"G{i}" for i in range(12)], name="gene"),
        columns=["ctrl1", "ctrl2", "ctrl3", "trt1", "trt2", "trt3"],
    )
    frame["pathway"] = ["TF"] * 4 + ["Sarcomere"] * 4 + ["Cycle"] * 4
    return frame


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_heatmap_groups_nature(expression_matrix: pd.DataFrame) -> Figure:
    condition = {c: c[:-1] for c in expression_matrix.columns[:6]}
    return (
        sp.heatmap(expression_matrix)
        .scale("row")
        .groups(rows="pathway", cols=condition)
        .cluster(cols=False)
        .preset("nature", width="double")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_heatmap_correlation_values(expression_matrix: pd.DataFrame) -> Figure:
    corr = expression_matrix.drop(columns="pathway").corr()
    return (
        sp.heatmap(corr, square=True)
        .mask("upper", diagonal=True)
        .cmap("RdBu", center=0, vmin=-1, vmax=1)
        .values(".2f")
        .colorbar("Pearson r")
        .fig
    )


@pytest.fixture
def ages() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "age": np.r_[rng.normal(42, 9, 320), rng.normal(56, 7, 180)],
            "group": ["control"] * 320 + ["patient"] * 180,
        }
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_histogram_density_kde(ages: pd.DataFrame) -> Figure:
    return (
        sp.histogram(ages, x="age", hue="group", stat="density", binwidth=4)
        .kde()
        .refline("median")
        .show_n()
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_histogram_dodge_nature(ages: pd.DataFrame) -> Figure:
    return (
        sp.histogram(ages, x="age", hue="group", multiple="dodge", binwidth=5)
        .preset("nature")
        .fig
    )
