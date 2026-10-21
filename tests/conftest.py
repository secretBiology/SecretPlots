import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest

import SecretPlots as sp
from SecretPlots.core import fonts
from SecretPlots.errors import reset_once_warnings


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Unexpected SecretPlots warnings fail tests. Installed fonts differ per
    # machine, so font fallback is ignored here and tested in test_fonts.py.
    for item in items:
        item.add_marker(
            pytest.mark.filterwarnings("error::SecretPlots.SecretPlotsWarning")
        )
        item.add_marker(
            pytest.mark.filterwarnings("ignore::SecretPlots.FontFallbackWarning")
        )


@pytest.fixture(autouse=True)
def _clean_state():
    sp.reset()
    sp.config.strict = False
    reset_once_warnings()
    yield
    sp.reset()
    sp.config.strict = False


@pytest.fixture
def only_dejavu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend only matplotlib's bundled fonts are installed (deterministic)."""
    installed = {name.casefold(): name for name in ("DejaVu Sans", "DejaVu Serif")}
    monkeypatch.setattr(fonts, "_installed", lambda: installed)


@pytest.fixture
def expression() -> pd.DataFrame:
    genes = ["GATA4", "NKX2-5", "TBX5", "HAND2"]
    return pd.DataFrame(
        {
            "gene": genes * 6,
            "tpm": [12, 8, 15, 4, 13, 9, 14, 5, 11, 7, 16, 4] * 2,
            "sample": ["ctrl"] * 12 + ["treated"] * 12,
        }
    )
