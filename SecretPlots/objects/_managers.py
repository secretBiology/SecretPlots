#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 30/09/19, 10:11 AM
#
#
# All managers

import matplotlib
from SecretColors import ColorMap
from SecretColors.utils import text_color, rgb_to_hex
from matplotlib.pyplot import Axes, Figure

from SecretPlots.constants.graph import *
from SecretPlots.objects.base2 import *
from SecretPlots.objects.shapes import *


class Assembler:

    def __init__(self, fig: Figure, log: Log):
        self._log = log
        self._type = None
        self._data = None
        self._am = None
        self._lm = None
        self._fig = fig
        self._gm = None
        self._om = None
        self._cm = None
        self._em = None

        self._log.info("Assembler is initialized with default values")

    @property
    def gm(self):
        if self._gm is None:
            self._gm = GridManager(self._fig, self._log)
        return self._gm

    @property
    def om(self):
        if self._om is None:
            self._om = ObjectManager(self.am, self.cm, self._log)
        return self._om

    @property
    def am(self):
        if self._am is None:
            a = AxisManager(self.gm.get_main_axis(self.type), self._log)
            self._am = a
        return self._am

    @property
    def cm(self):
        if self._cm is None:
            self._cm = ColorManager(self.type, self._log)
        return self._cm

    @property
    def em(self):
        if self._em is None:
            self._em = ExtraManager(self.gm, self.am, self.cm, self._log)
        return self._em

    @property
    def ax(self):
        return self.am.ax

    @property
    def type(self):
        raise NotImplementedError

    @property
    def lm(self):
        raise NotImplementedError

    def draw(self):
        raise NotImplementedError

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def data(self) -> Data:
        return self._data

    @data.setter
    def data(self, value):
        self._data = Data(value, self._log)

    def _set_auto_limit(self):
        self.ax.set_xlim(self.om.min_x - self.am.x.padding_start,
                         self.om.max_x + self.am.x.padding_end)

        self.ax.set_ylim(self.om.min_y - self.am.y.padding_start,
                         self.om.max_y + self.am.y.padding_end)

        self._log.info("Axis limit is set automatically")

    def _check_axis_transformations(self):
        if self.am.x.is_inverted:
            self.ax.invert_xaxis()
        if self.am.y.is_inverted:
            self.ax.invert_yaxis()

    def _draw_axis(self):
        self._set_auto_limit()
        if len(self.am.x.ticks) != 0:
            self.ax.set_xticks(self.am.x.ticks)
            self.ax.set_xticklabels(self.am.x.tick_labels)
        if len(self.am.y.ticks) != 0:
            self.ax.set_yticks(self.am.y.ticks)
            self.ax.set_yticklabels(self.am.y.tick_labels)

        self.am.major.make_midlines()
        self.am.minor.make_midlines()
        self.em.draw_midlines()
        self.em.draw_edgelines()
        self._check_axis_transformations()


class GridManager:
    def __init__(self, fig: Figure, log: Log):
        self.fig = fig
        self._log = log
        self._log.info("GridManager is initialized with default values")
        self._main = None

    def _generate_axes(self, plot_type):
        if self._main is None:
            if plot_type != PLOT_COLOR_MAP:
                self._log.info("Plot Grid is set to normal.")
                self._main = self.fig.add_subplot(111)
            else:
                self._log.info("Plot Grid with colormap is generated")
                self._main = self.fig.add_subplot(111)

    def get_main_axis(self, plot_type) -> Axes:
        if self._main is None:
            self._generate_axes(plot_type)
        return self._main


class AxisManager:
    def __init__(self, ax: Axes, log: Log):
        self._log = log
        self._orientation = "x"

        self._log.info("AxisManager is initialized with default values")

        self._x = Axis("x", self._log)
        self._y = Axis("y", self._log)
        self._ax = ax
        self.is_reversed = False

    @property
    def orientation(self):
        return self._orientation.replace("-", "").replace("+", "")

    @orientation.setter
    def orientation(self, value: str):
        value = value.strip().lower()
        if value.replace("-", "").replace("+", "") not in ["x", "y"]:
            self._log.error("Invalid axis orientation. Allowed orientations "
                            "are x, y, -x, -y")

        self._orientation = value
        self._log.info("Axis orientation set to : {}".format(value))

        if self._orientation == "-x":
            self.y.is_inverted = True
        elif self._orientation == "-y":
            self.x.is_inverted = True

    @property
    def is_reflected(self):
        return "-" in self._orientation

    @property
    def ax(self):
        return self._ax

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def major(self):
        if self.orientation == "x":
            return self._x
        else:
            return self._y

    @property
    def minor(self):
        if self.orientation == "x":
            return self._y
        else:
            return self._x


class ColorManager:
    def __init__(self, plot_type: str, log: Log):
        self._log = log
        self.plot_type = plot_type
        self._palette = None
        self._unique_colors = []
        self._all_colors = {}
        self._cmap = None

        self._log.info("ColorManager is initialized with default values.")

    @property
    def palette(self) -> Palette:
        if self._palette is None:
            self._palette = Palette(show_warning=False)
        return self._palette

    @property
    def cmap(self):
        if self._cmap is None:
            colors = [self.palette.lime(shade=30), self.palette.lime(),
                      self.palette.brown(shade=40),
                      self.palette.brown(shade=80),
                      self.palette.black()]
            self._cmap = ColorMap(matplotlib, self.palette).from_list(colors)
        return self._cmap

    def _get_color(self, index, value):
        if index not in self._all_colors.keys():
            if index < len(self.palette.get_color_list):
                self._all_colors[index] = self.palette.get_color_list[index]
            else:
                self._all_colors[index] = self.palette.random()

        return self._all_colors[index]

    def _get_from_map(self, value):
        r, g, b, _ = self.cmap(value)
        return rgb_to_hex(r, g, b)

    def color(self, position, value):
        row, col = position
        if self.plot_type == PLOT_STACKED_BAR:
            return self._get_color(col, value)
        elif self.plot_type == PLOT_COLOR_MAP:
            return self._get_from_map(value)
        else:
            return self._get_color(row, value)


class ObjectManager:
    def __init__(self, am: AxisManager, cm: ColorManager, log: Log):
        self._log = log
        self.am = am
        self.cm = cm
        self.is_point = False
        self.width = 1
        self.height = 1
        self.rotation = 0
        self._options = None
        self.shape = "r"
        self.max_x = 0
        self.max_y = 0
        self.min_x = 0
        self.min_y = 0
        self._log.info("ObjectManager is initialized with default values")

    @property
    def options(self):
        if self._options is None:
            self._options = {}
        return self._options

    def add_options(self, **kwargs):
        self._options = {**self.options, **kwargs}

    def _check_limits(self, x, y):
        if x > self.max_x:
            self.max_x = x
        elif x < self.min_x:
            self.min_x = x
        if y > self.max_y:
            self.max_y = y
        elif y < self.min_y:
            self.min_y = y

    def _get_bar_object(self, x, y, value, pos):
        e = Element(self._log)
        e.add_options(**self.options)
        e.add_options(color=self.cm.color(pos, value))
        e.shape = self.shape
        if self.am.orientation == "x":
            e.width = self.width
            e.height = value
        else:
            e.width = value
            e.height = self.width

        self._check_limits(x, y)
        self._check_limits(x + e.width, y + e.height)
        return e.get(x, y)

    def _get_heatmap_object(self, x, y, value, pos):
        e = Element(self._log)
        e.add_options(**self.options)
        e.add_options(color=self.cm.color(pos, value))
        e.shape = self.shape
        e.width = self.width
        e.height = self.height
        self._check_limits(x, y)
        self._check_limits(x + e.width, y + e.height)
        return e.get(x, y)

    def get(self, x, y, value, pos):
        if self.cm.plot_type in [PLOT_BAR, PLOT_STACKED_BAR]:
            return self._get_bar_object(x, y, value, pos)
        elif self.cm.plot_type == PLOT_COLOR_MAP:
            return self._get_heatmap_object(x, y, value, pos)


class ExtraManager:
    def __init__(self, gm: GridManager, am: AxisManager, cm: ColorManager,
                 log: Log):
        self.gm = gm
        self.cm = cm
        self.am = am
        self._log = log
        self.show_values = False
        self._value_options = None

        self._log.info("ExtraManager is initialized with default values")

    @property
    def value_options(self):
        if self._value_options is None:
            self._value_options = {
                "anchor": (0.5, 0.5),
                "relative": True,
                "offset": (0, 0)
            }
        return self._value_options

    def add_value_options(self, **kwargs):
        self._value_options = {**self.value_options, **kwargs}

    def draw_values(self, shape, text, bg_color):
        if not self.show_values:
            return

        opts = {"ha": "center", "color": text_color(bg_color)}

        opts = {**opts, **self.value_options}

        if opts["relative"]:
            x = shape.x + shape.width * opts["anchor"][0] + opts["offset"][0]
            y = shape.y + shape.height * opts["anchor"][1] + opts["offset"][1]
        else:
            x = shape.x + opts["anchor"][0] + opts["offset"][0]
            y = shape.y + opts["anchor"][1] + opts["offset"][1]

        if opts["anchor"][0] != 0.5 and opts["anchor"][1] != 0.5:
            del opts["ha"]

        del opts["anchor"]
        del opts["relative"]
        del opts["offset"]

        self.gm.get_main_axis(self.cm.plot_type).text(x, y, "{}".format(text),
                                                      **opts)

    def draw_midlines(self):
        if self.am.x.show_midlines:
            for x in self.am.x.midlines:
                self.am.ax.axvline(x, **self.am.x.midlines_options)

        if self.am.y.show_midlines:
            for y in self.am.y.midlines:
                self.am.ax.axhline(y, **self.am.y.midlines_options)

    def draw_edgelines(self):
        if self.am.x.show_edgelines:
            for x in self.am.x.edgelines:
                self.am.ax.axvline(x, **self.am.x.edgelines_options)

        if self.am.y.show_edgelines:
            for y in self.am.y.edgelines:
                self.am.ax.axhline(y, **self.am.y.edgelines_options)


def run():
    data = np.random.uniform(1, 3, 10)
