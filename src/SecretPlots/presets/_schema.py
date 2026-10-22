"""Strict conversion of TOML mappings into preset dataclasses."""

import types
from collections.abc import Mapping
from dataclasses import fields
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from SecretPlots.core.units import DEFAULT_PX_PER_INCH, to_inches
from SecretPlots.errors import PresetError
from SecretPlots.presets._model import Chrome, Preset, Target
from SecretPlots.theme import Theme

_TOP_LEVEL = {
    "name",
    "kind",
    "description",
    "official",
    "source_url",
    "verified_on",
    "disclaimer",
    "target",
    "theme",
    "chrome",
    "plots",
}

_NEWS_DISCLAIMER = (
    "Inspired by publicly visible chart conventions. Not affiliated with or "
    "endorsed by the publisher; uses open fallback fonts and no logos."
)


def _coerce(value: Any, tp: Any, where: str) -> Any:
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        options = [a for a in get_args(tp) if a is not type(None)]
        errors = []
        for option in options:
            try:
                return _coerce(value, option, where)
            except PresetError as exc:
                errors.append(str(exc))
        raise PresetError(
            errors[0] if len(errors) == 1 else f"{where}: invalid {value!r}"
        )
    if origin is Literal:
        allowed = get_args(tp)
        if value not in allowed:
            raise PresetError(f"{where}: {value!r} is not one of {list(allowed)}")
        return value
    if origin is tuple:
        if not isinstance(value, list | tuple):
            raise PresetError(f"{where}: expected a list, got {value!r}")
        item_type = get_args(tp)[0]
        return tuple(
            _coerce(v, item_type, f"{where}[{i}]") for i, v in enumerate(value)
        )
    if tp is float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise PresetError(f"{where}: expected a number, got {value!r}")
        return float(value)
    if tp in (str, bool):
        if not isinstance(value, tp):
            raise PresetError(f"{where}: expected {tp.__name__}, got {value!r}")
        return value
    raise PresetError(f"{where}: unsupported field type {tp!r}")  # pragma: no cover


def _build(
    cls: type, data: Mapping[str, Any], where: str, skip: set[str]
) -> dict[str, Any]:
    hints = get_type_hints(cls)
    known = {f.name for f in fields(cls)}
    unknown = set(data) - known
    if unknown:
        raise PresetError(f"{where}: unknown key(s) {sorted(unknown)}")
    return {
        key: _coerce(value, hints[key], f"{where}.{key}")
        for key, value in data.items()
        if key not in skip
    }


def _alias(key: str, value: Any) -> Any:
    # matplotlib-style shorthands: grid=True / grid=False
    if key == "grid" and isinstance(value, bool):
        return "both" if value else "none"
    return value


def _check(key: str, value: Any, where: str) -> Any:
    if key == "aspect" and value != "auto" and value <= 0:
        raise PresetError(f"{where}: aspect must be more than 0, got {value!r}")
    return value


def theme_from_mapping(data: Mapping[str, Any], *, name: str, where: str) -> Theme:
    data = {key: _alias(key, value) for key, value in data.items()}
    kwargs = _build(Theme, data, where, skip=set())
    for key, value in kwargs.items():
        _check(key, value, f"{where}.{key}")
    kwargs.setdefault("name", name)
    return Theme(**kwargs)


def coerce_theme_field(key: str, value: Any) -> Any:
    """Validate one theme field value (lists become tuples, ints become floats)."""
    if value is None:
        return None
    where = f"theme {key}"
    value = _coerce(_alias(key, value), get_type_hints(Theme)[key], where)
    return _check(key, value, where)


def _target_from_mapping(data: Mapping[str, Any], where: str) -> Target:
    kwargs = _build(Target, data, where, skip={"widths", "max_height"})
    ppi = kwargs.get("px_per_inch", DEFAULT_PX_PER_INCH)
    raw_widths = data.get("widths")
    if not isinstance(raw_widths, Mapping) or not raw_widths:
        raise PresetError(
            f"{where}.widths: expected a table like {{ single = '89mm' }}"
        )
    try:
        kwargs["widths"] = {
            k: to_inches(v, px_per_inch=ppi) for k, v in raw_widths.items()
        }
        if "max_height" in data:
            kwargs["max_height"] = to_inches(data["max_height"], px_per_inch=ppi)
    except (TypeError, ValueError) as exc:
        raise PresetError(f"{where}: {exc}") from None
    kwargs.setdefault("default_width", next(iter(raw_widths)))
    return Target(**kwargs)


def preset_from_mapping(data: Mapping[str, Any], *, source: str) -> Preset:
    """Validate and convert a parsed TOML document into a :class:`Preset`."""
    unknown = set(data) - _TOP_LEVEL
    if unknown:
        raise PresetError(f"{source}: unknown key(s) {sorted(unknown)}")
    for required in ("name", "kind", "target"):
        if required not in data:
            raise PresetError(f"{source}: missing required key {required!r}")

    name = _coerce(data["name"], str, f"{source}.name")
    kind = _coerce(
        data["kind"], Literal["journal", "news", "generic"], f"{source}.kind"
    )
    meta = {
        k: _coerce(data[k], bool if k == "official" else str, f"{source}.{k}")
        for k in ("description", "official", "source_url", "verified_on", "disclaimer")
        if k in data
    }
    if kind == "news" and not meta.get("official", False):
        meta.setdefault("disclaimer", _NEWS_DISCLAIMER)

    plots_raw = data.get("plots", {})
    if not isinstance(plots_raw, Mapping):
        raise PresetError(f"{source}.plots: expected tables like [plots.bar]")

    return Preset(
        name=name,
        kind=kind,
        target=_target_from_mapping(data["target"], f"{source}.target"),
        theme=theme_from_mapping(
            data.get("theme", {}), name=name, where=f"{source}.theme"
        ),
        chrome=Chrome(
            **_build(Chrome, data.get("chrome", {}), f"{source}.chrome", set())
        ),
        plots={
            kind_: theme_from_mapping(
                table, name=f"{name}:{kind_}", where=f"{source}.plots.{kind_}"
            )
            for kind_, table in plots_raw.items()
        },
        **meta,
    )
