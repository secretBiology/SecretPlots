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

from collections import defaultdict

import matplotlib.pyplot as plt
from SecretColors import Palette
from SecretColors.utils import text_color
from matplotlib.lines import Line2D

from SecretPlots.constants.network import *
from SecretPlots.network.pathfinder import *
from SecretPlots.objects.shapes import Rectangle


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


def get_direction(p1, p2, p3):
    def _check(x1, x2, y1, y2):
        if x1 == x2:
            if y1 < y2:
                return BOTTOM
            else:
                return TOP
        else:
            if x1 < x2:
                return LEFT
            else:
                return RIGHT

    input_direction = _check(p1[0], p2[0], p1[1], p2[1])
    output_direction = _check(p3[0], p2[0], p3[1], p2[1])

    return input_direction, output_direction


def check_line_direction(gap: Gap, pg: Union[Gap, None], ng: Union[Gap, None]):
    x2, y2 = gap.column, gap.row
    if pg is None:
        x1, y1 = gap.column, gap.row + 1
    else:
        x1, y1 = pg.column, pg.row
    if ng is None:
        x3, y3 = gap.column, gap.row - 1
    else:
        x3, y3 = ng.column, ng.row

    return get_direction((x1, y1), (x2, y2), (x3, y3))


def draw_line(ax, gap: Gap, pg: Gap, ng: Gap, row_slots: Dict,
              col_slots: Dict, line: str, color: str):
    rf = row_slots[gap.row]
    f = 1 / (len(rf) + 1)
    col_factor = f + f * rf.index(line)

    cf = col_slots[gap.column]
    e = 1 / (len(cf) + 1)
    row_factor = e + e * cf.index(line)

    def _points(direction):
        if direction == LEFT:
            x.append(gap.x)
            y.append(gap.y + gap.height * col_factor)
        elif direction == RIGHT:
            x.append(gap.x + gap.width)
            y.append(gap.y + gap.height * col_factor)
        elif direction == TOP:
            x.append(gap.x + gap.width * row_factor)
            y.append(gap.y + gap.height)
        else:
            x.append(gap.x + gap.width * row_factor)
            y.append(gap.y)

    in_dir, out_dir = check_line_direction(gap, pg, ng)
    x = []
    y = []
    if pg is None and ng is None:
        x.extend(
            [gap.x + gap.width * row_factor,
             gap.x + gap.width * row_factor]
        )
        y.extend(
            [gap.y + gap.height, gap.y]
        )
    elif pg is None:
        x.extend(
            [gap.x + gap.width / 2, gap.x + gap.width / 2])
        y.extend([gap.y + gap.height,
                  gap.y + gap.height * col_factor,
                  gap.y + gap.height * col_factor])
        if out_dir == LEFT:
            x.append(gap.x)
        else:
            x.append(gap.x + gap.width)

    else:

        _points(in_dir)

        x.append(gap.x + gap.width * row_factor)
        y.append(gap.y + gap.height * col_factor)

        if ng is None:
            x.append(gap.x + gap.width * row_factor)
            y.append(gap.y)

        else:
            _points(out_dir)

    line = Line2D(x, y, color=color)
    ax.add_line(line)


def arrange_lines(data: np.ndarray):
    # NOTE: This function will modify the original data
    # Assign gaps
    row_slots = defaultdict(list)
    col_slots = defaultdict(list)
    for item in data.flatten():
        if not item.is_gap:
            for val in item.paths:
                for _, r, c in item.paths[val]:
                    if item.name not in row_slots[r]:
                        row_slots[r].append(item.name)
                    if item.name not in col_slots[c]:
                        col_slots[c].append(item.name)
                    data[r, c].add_line(item.name)

    # Assign slots
    for item in data.flatten():  # type: Union[Gap, Node]
        if item.is_gap:
            item.h_slots = len(row_slots[item.row])
            item.v_slots = len(col_slots[item.column])

    return row_slots, col_slots


def plot_network(data):
    def _color_cycle():
        for p in Palette():
            yield p

    palette = _color_cycle()
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

        all_x.extend([m.x, m.x + m.width])
        all_y.extend([m.y, m.y + m.height])
        if not m.is_gap:
            r = Rectangle(m.x, m.y, height=m.height, width=m.width,
                          color=next(palette))
            m.color = r.color
            ax.add_patch(r.get())
            add_text(ax, r, m.name)
            all_nodes[m.name] = m

    # Draw Lines
    row_slots, col_slots = arrange_lines(space.get())

    for n in all_nodes.values():
        for b in n.paths:
            vals = [space.matrix[x[1], x[2]] for x in n.paths[b]]
            vals.insert(0, None)
            vals.append(None)
            for i in range(len(vals))[1:-1]:
                draw_line(ax, vals[i], vals[i - 1], vals[i + 1],
                          row_slots, col_slots, n.name, n.color)

    ax.set_xlim(min(all_x), max(all_x))
    ax.set_ylim(min(all_y), max(all_y))
    plt.show()


def run():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["c", "d", 1],
        ["c", "a", 1],
        ["c", "ta", 1],
    ]

    plot_network(data)
