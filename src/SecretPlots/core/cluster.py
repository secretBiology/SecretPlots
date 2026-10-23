"""Agglomerative (hierarchical) clustering in numpy, for heatmap row/column order.

Implements the Lance-Williams update with cached nearest neighbours, which is
O(n²) memory and close to O(n²) time for typical data. Results match
``scipy.cluster.hierarchy.linkage`` for the same method and metric (up to the
order of tied merges).
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np

Method = Literal["average", "complete", "single", "ward"]
Metric = Literal["euclidean", "correlation", "cosine"]

METHODS: tuple[str, ...] = ("average", "complete", "single", "ward")
METRICS: tuple[str, ...] = ("euclidean", "correlation", "cosine")


@dataclass(frozen=True)
class Tree:
    """Merge history of ``n`` leaves, like scipy's linkage matrix.

    ``merges[k] = (a, b, height)`` joins clusters ``a`` and ``b`` into cluster
    ``n + k``; ids below ``n`` are leaves. ``order`` is the left-to-right leaf
    order of the dendrogram.
    """

    n: int
    merges: tuple[tuple[int, int, float], ...]
    order: tuple[int, ...]


def distances(values: np.ndarray, metric: Metric = "euclidean") -> np.ndarray:
    """Pairwise distances between the rows of ``values``."""
    if metric not in METRICS:
        raise ValueError(f"Unknown metric {metric!r}. Use one of {METRICS}.")
    x = np.asarray(values, dtype=float)
    if metric == "euclidean":
        # Centring leaves distances unchanged but stops ||x||^2 + ||y||^2 - 2x.y
        # from cancelling catastrophically when values share a large offset.
        x = x - x.mean(axis=0)
        sq = np.sum(x**2, axis=1)
        d2 = sq[:, None] + sq[None, :] - 2 * x @ x.T
        return np.asarray(np.sqrt(np.clip(d2, 0, None)), dtype=float)
    if metric == "correlation":
        x = x - x.mean(axis=1, keepdims=True)
    norm = np.linalg.norm(x, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        unit = x / norm[:, None]
    unit = np.nan_to_num(unit)  # constant rows: no direction, distance 1
    return np.asarray(np.clip(1 - unit @ unit.T, 0, 2), dtype=float)


def linkage(
    values: np.ndarray, method: Method = "average", metric: Metric = "euclidean"
) -> Tree:
    """Cluster the rows of ``values``."""
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}. Use one of {METHODS}.")
    if method == "ward" and metric != "euclidean":
        raise ValueError("method='ward' needs metric='euclidean'")
    n = len(values)
    if n < 2:
        return Tree(n, (), tuple(range(n)))
    d = distances(values, metric)
    if method == "ward":
        d = d**2
    np.fill_diagonal(d, np.inf)

    size = np.ones(n)
    ident = list(range(n))  # cluster id currently stored in each slot
    first = list(range(n))  # smallest original index in each slot's cluster
    children: dict[int, tuple[int, int]] = {}
    active = np.ones(n, bool)
    nearest = np.argmin(d, axis=1)
    nearest_d = d[np.arange(n), nearest]
    merges: list[tuple[int, int, float]] = []

    for step in range(n - 1):
        i = int(np.argmin(np.where(active, nearest_d, np.inf)))
        j = int(nearest[i])
        height = float(d[i, j])
        ni, nj = size[i], size[j]
        di, dj = d[i].copy(), d[j].copy()
        if method == "single":
            new = np.minimum(di, dj)
        elif method == "complete":
            new = np.maximum(di, dj)
        elif method == "average":
            new = (ni * di + nj * dj) / (ni + nj)
        else:
            total = ni + nj + size
            new = ((ni + size) * di + (nj + size) * dj - size * height) / total
        new[~active] = np.inf
        new[i] = new[j] = np.inf
        d[i, :] = d[:, i] = new
        d[j, :] = d[:, j] = np.inf
        active[j] = False
        nearest_d[j] = np.inf

        a, b = ident[i], ident[j]
        if first[j] < first[i]:  # earlier data first keeps the input order stable
            a, b = b, a
        merged = n + step
        children[merged] = (a, b)
        merges.append((a, b, float(np.sqrt(height)) if method == "ward" else height))
        ident[i] = merged
        size[i] = ni + nj
        first[i] = min(first[i], first[j])

        stale = active & ((nearest == i) | (nearest == j))
        stale[i] = True
        for k in np.flatnonzero(stale):
            nearest[k] = int(np.argmin(d[k]))
            nearest_d[k] = d[k, nearest[k]]
        closer = active & (new < nearest_d)
        nearest[closer] = i
        nearest_d[closer] = new[closer]

    order: list[int] = []
    stack = [n + len(merges) - 1]
    while stack:
        node = stack.pop()
        if node < n:
            order.append(node)
        else:
            left, right = children[node]
            stack += [right, left]
    return Tree(n, tuple(merges), tuple(order))


def dendrogram_segments(tree: Tree) -> list[tuple[list[float], list[float]]]:
    """Line segments ``(positions, heights)`` of the dendrogram, one "⊓" per
    merge, with leaf ``order[k]`` at position ``k``."""
    position: dict[int, float] = {leaf: float(k) for k, leaf in enumerate(tree.order)}
    height: dict[int, float] = dict.fromkeys(range(tree.n), 0.0)
    segments = []
    for step, (a, b, h) in enumerate(tree.merges):
        node = tree.n + step
        pa, pb = position[a], position[b]
        segments.append(([pa, pa, pb, pb], [height[a], h, h, height[b]]))
        position[node] = (pa + pb) / 2
        height[node] = h
    return segments


def cut(tree: Tree, k: int) -> np.ndarray:
    """Cluster label (0..k-1) of every leaf when the tree is cut into ``k``
    clusters. Labels are numbered in dendrogram order, left to right."""
    if not 1 <= k <= tree.n:
        raise ValueError(f"Cannot cut {tree.n} items into {k} clusters")
    parent = list(range(tree.n))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    members: dict[int, int] = {}  # cluster id -> a leaf in it
    for step, (a, b, _) in enumerate(tree.merges[: tree.n - k]):
        la = a if a < tree.n else members[a]
        lb = b if b < tree.n else members[b]
        parent[root(lb)] = root(la)
        members[tree.n + step] = la
    labels = np.empty(tree.n, int)
    numbering: dict[int, int] = {}
    for leaf in tree.order:
        labels[leaf] = numbering.setdefault(root(leaf), len(numbering))
    return labels
