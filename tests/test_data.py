import numpy as np
import pandas as pd
import pytest

import SecretPlots as sp
from SecretPlots.core.data import tidy


def test_long_dataframe(expression: pd.DataFrame) -> None:
    t = tidy(expression, x="gene", y="tpm", hue="sample")
    assert t.x_order == ["GATA4", "NKX2-5", "TBX5", "HAND2"]
    assert t.hue_order == ["ctrl", "treated"]
    assert (t.x_name, t.y_name, t.hue_name) == ("gene", "tpm", "sample")


def test_wide_dataframe_becomes_groups() -> None:
    df = pd.DataFrame(
        {"ctrl": [1, 2], "treated": [3, 4]}, index=pd.Index(["a", "b"], name="gene")
    )
    t = tidy(df)
    assert t.hue_order == ["ctrl", "treated"]
    assert t.x_name == "gene"


def test_series() -> None:
    t = tidy(pd.Series([1, 2], index=["a", "b"], name="tpm"))
    assert t.x_order == ["a", "b"]
    assert t.y_name == "tpm"


def test_dict_scalar_replicates_and_nested() -> None:
    assert tidy({"a": 1, "b": 2}).x_order == ["a", "b"]
    assert len(tidy({"a": [1, 2, 3], "b": [4]}).frame) == 4
    nested = tidy({"a": {"x": 1, "y": 2}, "b": {"x": 3, "y": 4}})
    assert nested.hue_order == ["x", "y"]


def test_list_and_matrix() -> None:
    assert tidy([3, 1, 2]).x_order == [0, 1, 2]
    matrix = tidy(np.arange(6).reshape(2, 3))
    assert matrix.x_order == [0, 1]
    assert matrix.hue_order == [0, 1, 2]


def test_categorical_order_respected() -> None:
    df = pd.DataFrame(
        {"g": pd.Categorical(["b", "a"], categories=["a", "b"]), "v": [1, 2]}
    )
    assert tidy(df, x="g", y="v").x_order == ["a", "b"]


@pytest.mark.parametrize(
    ("data", "kwargs", "message"),
    [
        ([[1, 2], [3]], {}, "unequal length"),
        (pd.DataFrame({"a": [1]}), {"x": "a", "y": "missing"}, "not found"),
        (pd.DataFrame({"a": [1]}), {"x": "a"}, "y="),
        ([1, 2], {"x": "a", "y": "b"}, "column names"),
        (pd.DataFrame({"g": ["a"], "v": ["high"]}), {"x": "g", "y": "v"}, "numeric"),
        (pd.DataFrame({"g": ["a"]}), {}, "no numeric"),
        (np.zeros((2, 2, 2)), {}, "3-D"),
    ],
)
def test_bad_inputs(data: object, kwargs: dict[str, str], message: str) -> None:
    with pytest.raises(sp.DataShapeError, match=message):
        tidy(data, **kwargs)


def test_order_must_cover_data() -> None:
    with pytest.raises(sp.DataShapeError, match="missing"):
        tidy({"a": 1, "b": 2}, order=["a"])
