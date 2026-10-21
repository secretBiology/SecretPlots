"""Style cascade: combine partial themes into one complete theme.

Layers are given highest priority first. For each field the first layer that
sets it wins. Some fields can be *derived* from a related field (e.g.
``primary`` from ``palette``): if the related field comes from a higher-priority
layer than the field itself, the field is derived from it instead. That way a
preset that only defines a palette still gets a matching primary color and
heatmap colormap, rather than inheriting the base theme's blue.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from SecretPlots.core.colors import derived_diverging, derived_sequential
from SecretPlots.theme import STYLE_FIELDS, Theme

Values = Mapping[str, Any]

#: field -> (source field, derivation). Sources must precede fields in STYLE_FIELDS.
DERIVATIONS: dict[str, tuple[str, Callable[[Values], Any]]] = {
    "axes_background": ("background", lambda v: v["background"]),
    "primary": ("palette", lambda v: v["palette"][0]),
    "highlight": ("primary", lambda v: v["primary"]),
    "muted": ("neutral", lambda v: v["neutral"]),
    "sequential": (
        "primary",
        lambda v: derived_sequential(v["primary"], v["background"]),
    ),
    "diverging": (
        "positive",
        lambda v: derived_diverging(v["negative"], v["positive"], v["background"]),
    ),
}


@dataclass(frozen=True)
class Layer:
    name: str
    theme: Theme


@dataclass(frozen=True)
class Cascade:
    theme: Theme
    provenance: Mapping[str, str]


def cascade(layers: Sequence[Layer]) -> Cascade:
    """Resolve every style field. The last layer must be complete."""
    values: dict[str, Any] = {}
    rank: dict[str, int] = {}
    provenance: dict[str, str] = {}

    for field in STYLE_FIELDS:
        own = next(
            (
                i
                for i, layer in enumerate(layers)
                if getattr(layer.theme, field) is not None
            ),
            None,
        )
        derivation = DERIVATIONS.get(field)
        if derivation is not None:
            source, derive = derivation
            if own is None or rank[source] < own:
                values[field] = derive(values)
                rank[field] = rank[source]
                origin = provenance[source]
                if not origin.startswith("derived from"):
                    origin = f"derived from {source} of {origin}"
                provenance[field] = origin
                continue
        if own is None:
            raise RuntimeError(f"Style field {field!r} is not set by any layer")
        values[field] = getattr(layers[own].theme, field)
        rank[field] = own
        provenance[field] = layers[own].name

    return Cascade(
        theme=replace(Theme(name="resolved"), **values), provenance=provenance
    )
