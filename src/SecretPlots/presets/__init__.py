"""Preset registry: journals, newsrooms and generic output formats.

>>> import SecretPlots as sp
>>> sp.presets.list(kind="journal")      # doctest: +SKIP
['nature']
>>> sp.presets.get("nature").target.widths["single"]   # inches
3.5039370078740157
"""

import builtins
import difflib
import tomllib
from importlib.resources import files
from os import PathLike
from pathlib import Path
from typing import Any

from SecretPlots.errors import PresetError, PresetNotFoundError
from SecretPlots.presets._model import Chrome, Preset, PresetKind, Target
from SecretPlots.presets._schema import preset_from_mapping

__all__ = ["Chrome", "Preset", "Target", "get", "list", "load", "register"]

#: Preset used when none is selected.
DEFAULT = "screen"

_registry: dict[str, Preset] = {}
_loaded_builtins = False


def _ensure_builtins() -> None:
    global _loaded_builtins
    if _loaded_builtins:
        return
    root = files("SecretPlots.presets").joinpath("data")
    for group in root.iterdir():
        if not group.is_dir():
            continue
        for entry in sorted(group.iterdir(), key=lambda e: e.name):
            if entry.name.endswith(".toml"):
                data = tomllib.loads(entry.read_text(encoding="utf-8"))
                preset = preset_from_mapping(data, source=f"{group.name}/{entry.name}")
                _registry[preset.name] = preset
    _loaded_builtins = True


def get(name: str) -> Preset:
    """Return a preset by name, e.g. ``"nature"`` or ``"ft-like"``."""
    _ensure_builtins()
    try:
        return _registry[name]
    except KeyError:
        close = difflib.get_close_matches(name, _registry, n=1)
        hint = f" Did you mean {close[0]!r}?" if close else ""
        raise PresetNotFoundError(
            f"No preset named {name!r}.{hint} See SecretPlots.presets.list()."
        ) from None


def list(kind: PresetKind | None = None) -> builtins.list[str]:
    """Names of registered presets, optionally filtered by kind."""
    _ensure_builtins()
    return sorted(n for n, p in _registry.items() if kind is None or p.kind == kind)


def load(path: str | PathLike[str]) -> Preset:
    """Parse and validate a preset TOML file without registering it."""
    path = Path(path)
    try:
        data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PresetError(f"{path}: invalid TOML ({exc})") from None
    return preset_from_mapping(data, source=str(path))


def register(
    preset: Preset | str | PathLike[str], *, overwrite: bool = False
) -> Preset:
    """Register a :class:`Preset` object or a TOML file path; returns the preset."""
    _ensure_builtins()
    obj = preset if isinstance(preset, Preset) else load(preset)
    if obj.name in _registry and not overwrite:
        raise PresetError(f"Preset {obj.name!r} exists; pass overwrite=True")
    _registry[obj.name] = obj
    return obj
