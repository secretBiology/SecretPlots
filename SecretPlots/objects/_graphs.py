#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 03/10/19, 3:57 PM
#
#
# All graph managers

from SecretPlots.objects._locations import *
from SecretPlots.objects._managers import Assembler
from SecretPlots.objects.shapes import *


class BarManager(Assembler):

    @property
    def type(self):
        if self.data.type in [Data.SINGLE_VALUED, Data.SIMPLE_CATEGORICAL]:
            return PLOT_BAR
        else:
            if self.data.is_single_point:
                return PLOT_BAR
            return PLOT_STACKED_BAR

    @property
    def lm(self):
        return BarLocations(self.am, self._log)

    def _adjust_defaults(self):
        self.am.major.gap = 0.2
        self.am.minor.padding_start = 0

    def _draw_elements(self):
        locations = self.lm.get(self.data)
        for loc, val, pos in zip(locations, self.data.value,
                                 self.data.positions):
            x, y = loc
            if self.am.orientation == "y":
                x, y = y, x

            shape = self.om.get(x, y, val, pos)
            self.ax.add_patch(shape.get())
            self.em.draw_values(shape, val, self.cm.color(pos, val))

        ticks = []
        edge = []
        for i, m in enumerate(locations):
            if i == 0:
                edge.append(m[0])
            elif i == len(locations) - 1:
                edge.append(m[0] + self.om.width)
            temp = round(m[0] + self.om.width / 2, 2)
            if temp not in ticks:
                ticks.append(temp)

        self.am.major.ticks = ticks
        self.am.major.edgelines = edge
        self.am.major.make_labels()  # TODO: Remove if user uses own

    def draw(self):
        self._adjust_defaults()
        self._draw_elements()
        self._draw_axis()


class ColorMapManager(Assembler):
    @property
    def lm(self):
        return ColorMapLocations(self.am, self._log)

    @property
    def type(self):
        return PLOT_COLOR_MAP

    def _adjust_defaults(self):
        # self.am.minor.padding_start = 1
        # self.am.minor.padding_end = 1
        # self.am.major.padding_start = 1
        # self.am.major.padding_end = 1
        pass

    def _draw_elements(self):
        locations = self.lm.get(self.data)
        for loc, val, pos in zip(locations, self.data.value,
                                 self.data.positions):
            x, y = loc
            if self.am.orientation == "y":
                x, y = y, x

            shape = self.om.get(x, y, val / max(self.data.value), pos)
            self.ax.add_patch(shape.get())
            self.em.draw_values(shape, val, self.cm.color(pos, val / max(
                self.data.value)))

        ticks_major = []
        ticks_minor = []
        edge_major = []
        edge_minor = []
        for i, m in enumerate(locations):
            if i == 0:
                edge_major.append(m[0])
                edge_minor.append(m[1])
            elif i == len(locations) - 1:
                edge_major.append(m[0] + self.om.width)
                edge_minor.append(m[1] + self.om.height)
            temp = round(m[0] + self.om.width / 2, 2)
            temp_minor = round(m[1] + self.om.height / 2, 2)
            if temp not in ticks_major:
                ticks_major.append(temp)
            if temp_minor not in ticks_minor:
                ticks_minor.append(temp_minor)

        self.am.major.ticks = ticks_major
        self.am.minor.ticks = ticks_minor
        self.am.major.edgelines = edge_major
        self.am.minor.edgelines = edge_minor

        self.am.major.make_labels()  # TODO: Remove if user uses own
        self.am.minor.make_labels()  # TODO: Remove if user uses own

    def draw(self):
        self._adjust_defaults()
        self._draw_elements()
        self._draw_axis()


class BarPlot:
    def __init__(self, data, fig: plt.Figure = None, log: Log = None):
        if fig is None:
            fig = plt.figure()
        self.fig = fig
        if log is None:
            log = Log()
        self._log = log
        self.manager = BarManager(self.fig, self._log)
        self.manager.data = data

    def show(self):
        self.manager.draw()
        plt.show()


class ColorPlot:
    def __init__(self, data, fig: plt.Figure = None, log: Log = None):
        if fig is None:
            fig = plt.figure()
        self.fig = fig
        if log is None:
            log = Log()
        self._log = log
        self.manager = ColorMapManager(self.fig, self._log)
        self.manager.data = data

    def show(self):
        self.manager.draw()
        plt.show()


def run():
    data = [[2, 1, 4], [5, 3, 1]]
    b = ColorPlot(data)
    b.show()
