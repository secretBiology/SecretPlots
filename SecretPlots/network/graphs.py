#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/19/19, 12:13 PM
#
#
# Network plots

import matplotlib.pyplot as plt
from SecretPlots.objects.shapes import Rectangle
from matplotlib.lines import Line2D
import numpy as np
from SecretColors.utils import text_color
from SecretPlots.network.pathfinder import Space, MatItem, Node
from typing import List, Union


def add_text(ax: plt.Axes, r: Rectangle, text):
    ax.text(
        r.x + r.width / 2,
        r.y + r.height / 2,
        text,
        ha="center",
        va="center",
        color=text_color(r.color),
        fontsize=18
    )


def draw_horizontal(ax: plt.Axes, b1: MatItem, b2: MatItem):
    line = Line2D([b1.x, b2.x], [b1.y + b1.height / 2, b2.y + b2.height / 2])
    ax.add_line(line)


def draw_vertical(ax: plt.Axes, b1: MatItem, b2: MatItem):
    line = Line2D(
        [b1.x + b1.width / 2, b2.x + b2.width / 2],
        [b1.y, b2.y]
    )
    ax.add_line(line)


def draw_line(ax, n1: Node, n2: Node, matrix):
    for ind in n1.paths:
        path = n1.paths[ind]
        for i, p in enumerate(path):
            if i < len(path) - 1:
                ii, r, c = path[i]
                ni, nr, nc = path[i + 1]
                if r == nr:
                    draw_horizontal(ax, matrix[ii], matrix[ni])
                elif c == nc:
                    draw_vertical(ax, matrix[ii], matrix[ni])


def plot_network(data):
    space = Space(data)
    s = [x for x in space.get().flatten()]  # type: List[Union[MatItem, Node]]
    # Add points to the node
    for i, m in enumerate(s):
        m.assign(i, space.matrix.shape[1])

    all_nodes = {}

    fig, ax = plt.subplots()  # type: Union[plt.Figure, plt.Axes]
    all_x = []
    all_y = []
    # Draw nodes
    for m in s:
        r = Rectangle(m.x, m.y, height=m.height, width=m.width)
        all_x.extend([r.x, r.x + r.width])
        all_y.extend([r.y, r.y + r.height])
        if not m.is_gap:
            ax.add_patch(r.get())
            add_text(ax, r, m.name)
            all_nodes[m.name] = m

    # Draw lines
    for m in data:
        draw_line(ax, all_nodes[m[0]], all_nodes[m[1]], s)
    ax.set_xlim(min(all_x), max(all_x))
    ax.set_ylim(min(all_y), max(all_y))
    plt.show()


def run():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["a", "d", 1],
    ]

    plot_network(data)
