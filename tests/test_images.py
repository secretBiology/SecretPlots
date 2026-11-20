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


@pytest.mark.mpl_image_compare(
    tolerance=TOLERANCE, savefig_kwargs={"facecolor": "auto"}
)
def test_mobile_wrapped_chrome() -> Figure:
    return (
        sp.bar({"Before": 3, "After": 4})
        .preset("ft-like", width="mobile")
        .size(height="4in")
        .chrome(
            title="A long but ordinary chart title explaining the result",
            subtitle="A compact figure with readable context",
            source="An extended source description that wraps inside the figure",
        )
        .fig
    )


@pytest.mark.mpl_image_compare(
    tolerance=TOLERANCE, savefig_kwargs={"facecolor": "auto"}
)
def test_dark_groups_with_redundant_styles() -> Figure:
    frame = pd.DataFrame(
        {f"Group {i + 1}": np.arange(6) * (i + 1) / 4 for i in range(4)}
    )
    return (
        sp.line(frame)
        .encode_groups()
        .theme("dark")
        .format_axis("y", decimals=1)
        .legend("top")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_narrow_long_category_labels() -> Figure:
    return (
        sp.bar(
            {
                "Untreated baseline control": 2,
                "Low treatment concentration": 4,
                "Medium treatment concentration": 6,
                "High treatment concentration": 5,
            }
        )
        .preset("nature")
        .size(height="80mm")
        .values(".0f")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_many_groups_wrapped_legend() -> Figure:
    frame = pd.DataFrame(
        {f"Experimental condition {i + 1}": [i, i + 1, i + 2] for i in range(6)}
    )
    return sp.line(frame).size(width="4in", height="4in").legend("top").fig


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


@pytest.fixture
def weights() -> pd.DataFrame:
    rng = np.random.default_rng(4)
    return pd.DataFrame(
        {
            "dose": np.repeat(["0", "10", "50"], 24),
            "weight": np.r_[
                rng.normal(20, 2, 24), rng.normal(21, 2.5, 24), rng.normal(25, 3, 24)
            ],
            "sex": np.tile(["F", "M"], 36),
        }
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_box_points_compare_nature(weights: pd.DataFrame) -> Figure:
    return (
        sp.box(weights, x="dose", y="weight")
        .points()
        .compare(ref="0", correction="holm")
        .show_n()
        .preset("nature")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_violin_split_quartiles(weights: pd.DataFrame) -> Figure:
    return sp.violin(
        weights, x="dose", y="weight", hue="sex", split=True, inner="quartiles"
    ).fig


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_raincloud_default(weights: pd.DataFrame) -> Figure:
    return sp.raincloud(weights, x="dose", y="weight").fig


@pytest.fixture
def mouse_weights() -> pd.DataFrame:
    rng = np.random.default_rng(5)
    rows = []
    for diet, slope in (("chow", 0.5), ("high-fat", 1.1), ("keto", 0.2)):
        for mouse in range(6):
            weight = 20 + slope * np.arange(10) + rng.normal(0, 0.5, 10).cumsum()
            rows += [
                {"day": d, "weight": w, "diet": diet, "mouse": mouse}
                for d, w in enumerate(weight)
            ]
    return pd.DataFrame(rows)


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_line_fan_endlabels(mouse_weights: pd.DataFrame) -> Figure:
    return (
        sp.line(mouse_weights, x="day", y="weight", hue="diet", error="pi")
        .errorbars(level=(0.5, 0.8, 0.95))
        .endlabels(values=".1f")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_line_bars_markers_nature(mouse_weights: pd.DataFrame) -> Figure:
    return (
        sp.line(
            mouse_weights, x="day", y="weight", hue="diet", style="diet", error="sem"
        )
        .errorbars("bars", dodge=0.4)
        .markers()
        .preset("nature")
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_line_units_gradient_fill(mouse_weights: pd.DataFrame) -> Figure:
    chow = mouse_weights[mouse_weights["diet"] == "chow"]
    return (
        sp.line(chow, x="day", y="weight", units="mouse")
        .fill(gradient=True)
        .refline(24, label=True)
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_area_stacked_percent() -> Figure:
    years = np.arange(2000, 2011)
    wide = pd.DataFrame(
        {
            "coal": 40 - 2.0 * (years - 2000),
            "gas": 25 + 0.5 * (years - 2000),
            "solar": 0.5 * 1.5 ** (years - 2000),
        },
        index=pd.Index(years, name="year"),
    )
    return sp.area(wide, stack="percent").endlabels().fig


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_fill_between_split() -> Figure:
    t = np.linspace(0, 10, 120)
    return (
        sp.fill_between(x=t, y1=np.sin(t) + 0.1 * t - 0.3)
        .split(labels=("above", "below"))
        .refline(0)
        .fig
    )


@pytest.mark.mpl_image_compare(tolerance=TOLERANCE)
def test_forest_groups_table_nature() -> Figure:
    trial = pd.DataFrame(
        {
            "variable": [None, "Age", "Age", "Sex", "Sex"],
            "subgroup": ["All patients", "<65 yr", ">=65 yr", "Male", "Female"],
            "patients": [4744, 2513, 2231, 3635, 1109],
            "hr": [0.74, 0.76, 0.72, 0.73, 0.79],
            "lower": [0.65, 0.63, 0.60, 0.63, 0.62],
            "upper": [0.85, 0.92, 0.87, 0.85, 1.01],
            "weight": [np.nan, 2513, 2231, 3635, 1109],
        }
    )
    return (
        sp.forest(
            trial,
            label="subgroup",
            estimate="hr",
            lower="lower",
            upper="upper",
            group="variable",
            weight="weight",
        )
        .summary("All patients")
        .table(
            left={"Patients": "patients"},
            right={"P for interaction": {"Age": 0.76, "Sex": 0.0004}},
            formats={"P for interaction": "p"},
        )
        .favours("Favours drug", "Favours placebo")
        .stripes()
        .preset("nature")
        .fig
    )


@pytest.mark.mpl_image_compare(
    tolerance=TOLERANCE, savefig_kwargs={"facecolor": "auto"}
)
def test_survival_risk_table_nature() -> Figure:
    rng = np.random.default_rng(1)
    arm = np.repeat(["Placebo", "Drug"], 60)
    event_time = rng.exponential(np.where(arm == "Drug", 30, 18))
    censor_time = rng.uniform(6, 48, len(arm))
    trial = pd.DataFrame(
        {
            "months": np.minimum(event_time, censor_time).round(1),
            "died": event_time <= censor_time,
            "arm": arm,
        }
    )
    return (
        sp.survival(trial, time="months", event="died", hue="arm")
        .risk_table("at_risk", "events", times=[0, 12, 24, 36, 48])
        .median()
        .pvalue()
        .hazard_ratio()
        .preset("nature")
        .fig
    )


@pytest.mark.mpl_image_compare(
    tolerance=TOLERANCE, savefig_kwargs={"facecolor": "auto"}
)
def test_decision_curve_ci_nature() -> Figure:
    rng = np.random.default_rng(7)
    score = rng.normal(size=400)
    logit = -1.6 + 1.3 * score
    biopsy = pd.DataFrame(
        {
            "cancer": rng.random(400) < 1 / (1 + np.exp(-logit)),
            "Full model": 1 / (1 + np.exp(-(logit + rng.normal(0, 0.3, 400)))),
            "Marker only": 1 / (1 + np.exp(-(-1.6 + 0.6 * score))),
        }
    )
    return (
        sp.decision_curve(
            biopsy,
            outcome="cancer",
            models=["Full model", "Marker only"],
            thresholds=np.arange(0.01, 0.61, 0.01),
        )
        .ci(n_boot=200)
        .preset("nature")
        .fig
    )
