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
from SecretPlots.utils import Log


class NetworkPlot:
    def __init__(self, data, fig: plt.Figure = None, log: Log = None):
        if log is None:
            log = Log()
        if fig is None:
            fig = plt.figure()

        self._log = log
        self.data = data
        self.palette = Palette()
        self._space = None
        self.fig = fig  # type: plt.Figure

        # Options
        self.use_dijkstra = True
        self.colors = None
        self.colors_mapping = None
        self.node_width = 1
        self.node_height = 1
        self.node_gap = 1
        self.max_columns = None
        self.aspect_ratio = None
        self.font_size = 13

        self._ax = None
        self._text_options = None
        self._line_options = None
        self._fig_drawn = False
        self._all_nodes = None

        self._log.info("Network Plot is initialized")

    @property
    def ax(self) -> plt.Axes:
        if self._ax is None:
            self._ax = self.fig.subplots()
        return self._ax

    @property
    def space(self) -> Space:
        if self._space is None:
            self._space = Space(self.data,
                                height=self.node_height,
                                width=self.node_width)
            self._space.use_dijkstra = self.use_dijkstra
            self.node_gap = self.node_gap
            if self.max_columns is not None:
                self._space.max_cols = self.max_columns
        return self._space

    def _color_cycle(self):
        while True:
            if self.colors is None:
                for p in self.palette:
                    yield p
            else:
                if type(self.colors) == str:
                    self.colors = [self.colors]
                for c in self.colors:
                    yield c

    @property
    def text_options(self) -> dict:
        if self._text_options is None:
            self._text_options = {
                "ha": "center",
                "va": "center",
                "fontsize": self.font_size
            }
        return self._text_options

    @property
    def line_options(self) -> dict:
        if self._line_options is None:
            self._line_options = {}
        return self._line_options

    @property
    def all_nodes(self) -> Dict[str, Node]:
        if self._all_nodes is None:
            self._draw_elements()
        return self._all_nodes

    def _add_text(self, r: Rectangle, text: str):
        self.ax.text(
            r.x + r.width / 2,
            r.y + r.height / 2,
            text,
            color=text_color(r.color),
            **self.text_options
        )

    def add_text_options(self, **kwargs):
        self._text_options = {**self.text_options, **kwargs}

    def add_line_options(self, **kwargs):
        self._line_options = {**self.line_options, **kwargs}

    @staticmethod
    def _get_direction(p1: tuple, p2: tuple, p3: tuple) -> tuple:
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

    def _check_line_direction(self,
                              gap: Gap, pg: Union[Gap, None],
                              ng: Union[Gap, None]) -> tuple:
        x2, y2 = gap.column, gap.row
        if pg is None:
            x1, y1 = gap.column, gap.row + 1
        else:
            x1, y1 = pg.column, pg.row
        if ng is None:
            x3, y3 = gap.column, gap.row - 1
        else:
            x3, y3 = ng.column, ng.row

        return self._get_direction((x1, y1), (x2, y2), (x3, y3))

    def _add_line(self,
                  gap: Gap,
                  pg: Gap,
                  ng: Gap,
                  row_slots: Dict,
                  col_slots: Dict,
                  line: str,
                  color: str):

        arrow_width = 0.05
        arrow_height = 0.1
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

        in_dir, out_dir = self._check_line_direction(gap, pg, ng)
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

        opts = {"color": color}
        opts = {**opts, **self.line_options}
        line = Line2D(x, y, **opts)
        self.ax.add_line(line)

        if ng is None:
            # This is last block, add arrow
            arrow_x = [
                gap.x + gap.width * row_factor - arrow_width,
                gap.x + gap.width * row_factor,
                gap.x + gap.width * row_factor + arrow_width
            ]
            arrow_y = [
                gap.y + arrow_height,
                gap.y,
                gap.y + arrow_height
            ]

            arrow_line = Line2D(arrow_x, arrow_y, **opts)
            self.ax.add_line(arrow_line)

    @staticmethod
    def _arrange_lines(data: np.ndarray):
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

    def _draw_lines(self):
        # Draw Lines
        row_slots, col_slots = self._arrange_lines(self.space.get())

        for n in self.all_nodes.values():
            for b in n.paths:
                vals = [self.space.matrix[x[1], x[2]] for x in n.paths[b]]
                vals.insert(0, None)
                vals.append(None)
                for i in range(len(vals))[1:-1]:
                    self._add_line(vals[i],
                                   vals[i - 1],
                                   vals[i + 1],
                                   row_slots,
                                   col_slots,
                                   n.name,
                                   n.color)

    def _get_color(self, node_name, cycle) -> str:
        if self.colors_mapping is None:
            return next(cycle)
        else:
            if node_name in self.colors_mapping.keys():
                return self.colors_mapping[node_name]
            else:
                return next(cycle)

    def _draw_elements(self):
        if self._all_nodes is not None:
            self._log.warn("Elements have been already drawn")
            return

        palette = self._color_cycle()
        s = [x for x in
             self.space.get().flatten()]  # type: List[Union[MatItem, Node]]
        # Add points to the node
        for i, m in enumerate(s):
            m.assign(i, self.space.matrix.shape[1])

        all_nodes = {}

        all_x = []
        all_y = []
        # Draw nodes
        for m in s:
            all_x.extend([m.x, m.x + m.width])
            all_y.extend([m.y, m.y + m.height])
            if not m.is_gap:
                r = Rectangle(m.x, m.y, height=m.height, width=m.width,
                              color=self._get_color(m.name, palette))
                m.color = r.color
                self.ax.add_patch(r.get())
                self._add_text(r, m.name)
                all_nodes[m.name] = m

        self._all_nodes = all_nodes
        self.ax.set_xlim(min(all_x), max(all_x))
        self.ax.set_ylim(min(all_y), max(all_y))
        self._log.info("All nodes arranged in the space")

    def draw(self):
        # Sanity check to avoid redrawing
        if self._fig_drawn:
            self._log.warn("Figure is already drawn.")
            return
        else:
            self._fig_drawn = True

        self._draw_elements()
        self._draw_lines()
        self.ax.set_axis_off()
        if self.aspect_ratio is not None:
            self.ax.set_aspect(self.aspect_ratio)

    def show(self, tight=False):
        self.draw()
        if tight:
            plt.tight_layout()
        plt.show()

    def save(self, filename, **kwargs):
        self.draw()
        plt.savefig(filename, **kwargs)


def run():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["c", "d", 1],
        ["c", "a", 1],
        ["c", "a1", 1],
        ["c", "a2", 1],
        ["c", "a2", 1],
        ["c", "ae2", 1],
        ["c", "ae32", 1],
        ["c", "ta", 1],
        ["b", "ta", 1],
    ]

    n = NetworkPlot(data)
    n.show()
