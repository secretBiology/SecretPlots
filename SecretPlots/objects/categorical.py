#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 28/09/19, 1:06 AM
#
#
#

import matplotlib
from SecretColors import ColorMap
from SecretColors.utils import hex_to_rgba
from matplotlib.gridspec import GridSpec

from SecretPlots.objects.base import *


class HeatMap(Assembler):

    def __init__(self, data, fig: plt.Figure = None, _log: Log = None,
                 show_log: bool = False):
        if fig is None:
            fig = plt.figure()
        if _log is None:
            _log = Log(show_log=show_log)
        super().__init__(fig, _log)
        self._main_data = data
        self._additional_data = []
        self._log = _log
        self._log.info("HeatMap initialized")

        self._cmap = None
        self._padding_changed = False
        self._all_x = []
        self._all_y = []
        self._colorbar_loc = None
        self._ax_colormap = None
        self._remove_frame = None
        self.shape = "r"
        self.aspect_ratio = None

    @property
    def ax_grid(self):
        if self._ax_grid is None:
            self._log.info("Default GridSpec with 3 rows and 3 columns is "
                           "generated")
            self._ax_grid = GridSpec(3, 3,
                                     width_ratios=[1, 15, 1],
                                     height_ratios=[1, 15, 1],
                                     figure=self.fig)
        return self._ax_grid

    @property
    def ax(self) -> plt.Axes:
        if self._base_ax is None:
            if self._colorbar_loc is None:
                self._base_ax = self.fig.add_subplot(111)
            else:
                if self._colorbar_loc == "right":
                    main = self.ax_grid[:, :-1]
                elif self._colorbar_loc == "left":
                    main = self.ax_grid[:, 1:]
                elif self._colorbar_loc == "top":
                    main = self.ax_grid[1:, :]
                elif self._colorbar_loc == "bottom":
                    main = self.ax_grid[:-1, :]
                else:
                    self._log.error("'{}' position for colorbar is not valid "
                                    "".format(self._colorbar_loc))

                self._base_ax = self.fig.add_subplot(main)
        return self._base_ax

    @property
    def ax_colorbar(self) -> plt.Axes:
        if self._ax_colormap is None:
            if self._colorbar_loc == "right":
                col = self.ax_grid[:, -1]
            elif self._colorbar_loc == "left":
                col = self.ax_grid[:, 0]
            elif self._colorbar_loc == "top":
                col = self.ax_grid[0, :]
            elif self._colorbar_loc == "bottom":
                col = self.ax_grid[-1, :]
            else:
                self._log.error("'{}' position for colorbar is not valid "
                                "".format(self._colorbar_loc))

            self._ax_colormap = self.fig.add_subplot(col)

        return self._ax_colormap

    @property
    def xtickslabels(self):
        return self.am.x.ticks_labels

    @xtickslabels.setter
    def xtickslabels(self, values):
        self.am.x.ticks_labels = values

    @property
    def ytickslabels(self):
        return self.am.y.ticks_labels

    @ytickslabels.setter
    def ytickslabels(self, values):
        self.am.y.ticks_labels = values

    @property
    def x(self):
        return self.am.x

    @property
    def y(self):
        return self.am.y

    @property
    def cmap(self):
        if self._cmap is None:
            colors = [self.palette.lime(shade=30), self.palette.lime(),
                      self.palette.brown(shade=40),
                      self.palette.brown(shade=80),
                      self.palette.black()]
            self._cmap = ColorMap(matplotlib, self.palette).from_list(colors)
        return self._cmap

    def _get_color(self, value):
        m = max([x.max for x in self.sections])
        n = max([x.min for x in self.sections])
        if m == n:
            # Its single value
            return self.palette.red(shade=40)
        norm = matplotlib.colors.Normalize(vmin=n, vmax=m)
        return self.cmap(norm(value))

    def _draw_axis(self):
        # TODO: Handle this in the axis object
        if self.x.show_ticks:
            self.ax.set_xticks(self.am.x.ticks)
        else:
            self.ax.set_xticks([])

        if self.y.show_ticks:
            self.ax.set_yticks(self.am.y.ticks)
        else:
            self.ax.set_yticks([])

        self.ax.set_xticklabels(self.am.x.ticks_labels)
        self.ax.set_yticklabels(self.am.y.ticks_labels)

        self.ax.set_xlim(
            min(self._all_x) - self.am.x.padding[0],
            max(self._all_x) + self.am.x.padding[1]
        )

        self.ax.set_ylim(
            min(self._all_y) - self.am.y.padding[0],
            max(self._all_y) + self.am.y.padding[1]
        )

        if self._remove_frame:
            self.ax.spines['left'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['bottom'].set_visible(False)

        if self.aspect_ratio is not None:
            self.ax.set_aspect(self.aspect_ratio)

        if self.x.is_inverted:
            self.ax.invert_xaxis()
        if self.y.is_inverted:
            self.ax.invert_yaxis()

    def _draw_elements(self):
        # TODO : Need some cleaner way
        x_ticks = []
        y_ticks = []
        self._all_x = []
        self._all_y = []
        x = 0
        y = 0
        for section in self.sections:
            pos, next_boundary = self.am.get_positions(section, x, y,
                                                       self.width,
                                                       self.height)
            all_shapes = []
            for p, v in zip(pos, section.sequence):
                x_ticks.append(p[0] + self.width / 2)
                y_ticks.append(p[1] + self.height / 2)
                self._all_x.extend([p[0], p[0] + self.width])
                self._all_y.extend([p[1], p[1] + self.height])

                e = Element(self._log)
                e.x = p[0]
                e.y = p[1]
                e.height = self.height
                e.width = self.width
                e.shape = self.shape
                color = self._get_color(v)
                e.add_options(color=color)
                if self.show_missing or not np.isnan(v):
                    if np.isnan(v):
                        e.add_options(fill=False, hatch="//",
                                      color=hex_to_rgba(self.palette.gray(),
                                                        1))
                    shape = e.shape
                    self.ax.add_patch(shape.get())
                    self._draw_text(shape, v, color)
                    all_shapes.append(shape)
                else:
                    self._log.warn("Skipped Missing at location {}".format(p))

            nx = next_boundary[0] - section.section_gap
            ny = next_boundary[1] - section.section_gap
            self._draw_boundaries((x, y), (nx, ny))
            x, y = next_boundary

            # Set Ticks
            self.am.x.ticks = list(set(x_ticks))
            self.am.y.ticks = list(set(y_ticks))
            # Set Lines
            x_lines = []
            y_lines = []
            for i, m in enumerate(all_shapes[:-1]):
                if m.x != all_shapes[i + 1].x:
                    x1 = m.x + m.width
                    x2 = all_shapes[i + 1].x
                    x_lines.append((x1 + x2) / 2)
                if m.y != all_shapes[i + 1].y:
                    y1 = m.y + m.height
                    y2 = all_shapes[i + 1].y
                    y_lines.append((y1 + y2) / 2)

            x_lines = list(set(x_lines))
            y_lines = list(set(y_lines))
            for m in x_lines:
                self._draw_lines(m, None)
            for m in y_lines:
                self._draw_lines(None, m)

    def _prepare_data(self):
        self.add_section(self._main_data, gap=self.section_gap)
        for a in self._additional_data:
            self.add_section(a, gap=self.section_gap)

        # Initial y padding if padding has not defined
        if not self._padding_changed:
            self.am.y.padding = (0, 1)

    def _draw_colorbar(self):
        if self._colorbar_loc is None:
            return

        m = max([x.max for x in self.sections])
        n = min([x.min for x in self.sections])
        norm = matplotlib.colors.Normalize(vmin=n, vmax=m)
        sm = plt.cm.ScalarMappable(cmap=self.cmap, norm=norm)

        if self._colorbar_loc in ["right", "left"]:
            ori = "vertical"
        else:
            ori = "horizontal"

        plt.colorbar(sm, cax=self.ax_colorbar, orientation=ori)

        if self._colorbar_loc == "left":
            self.ax_colorbar.yaxis.set_ticks_position('left')
        elif self._colorbar_loc == "top":
            self.ax_colorbar.xaxis.set_ticks_position("top")

    def _draw_text(self, shape, text, color):
        if not self._text:
            return

        self._add_text(shape, text, color)

    def _draw_lines(self, loc_x, loc_y):
        if self.am.x.show_midlines:
            if loc_x is not None:
                self.ax.axvline(loc_x, **self.am.x.midline_options)

        if self.am.y.show_midlines:
            if loc_y is not None:
                self.ax.axhline(loc_y, **self.am.y.midline_options)

    def _draw_boundaries(self, start, end):
        if not self.section_boundary:
            return

        if self.am.orientation == "x":
            self.ax.axvspan(start[0], end[0], **self.section_boundary_options)
        else:
            self.ax.axhspan(start[1], end[1], **self.section_boundary_options)

    def draw(self):
        self._prepare_data()
        self._draw_elements()
        self._draw_axis()  # Always use after elements have set
        self._draw_colorbar()
        self._fig_drawn = True
        if self._colorbar_loc is None:
            return self.ax
        else:
            return self.ax, self.ax_colorbar

    def remove_frame(self):
        self._remove_frame = True

    def add_data(self, data):
        self._additional_data.append(data)

    def swap_axis(self):
        self.am.swap_axis(self._padding_changed)
        self._padding_changed = True

    def add_cmap(self, name):
        self._cmap = matplotlib.cm.get_cmap(name)

    def add_colorbar(self, loc="right"):
        self._colorbar_loc = loc
        self._log.info("Colormap location set to {}".format(loc))

    def show_colorbar(self, loc="right"):
        self.add_colorbar(loc)

    def show_values(self, anchor=None, **kwargs):
        self._text = True
        if anchor is None:
            anchor = (0.5, 0.5)
        self.add_text_options(anchor=anchor)
        self.add_text_options(**kwargs)

    def add_values(self, anchor=None, **kwargs):
        self.show_values(anchor, **kwargs)

    def padding(self, start, end=None, bottom=None, top=None):
        self.am.padding(start, end, bottom, top)
        self._padding_changed = True


def run():
    data = [np.random.uniform(0, 10, 5) for x in range(3)]
    h = HeatMap(data)
    h.add_data([[3, 6, 9], [1, 2]])
    h.show()
