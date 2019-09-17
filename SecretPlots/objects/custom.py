#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 15/09/19, 12:51 PM
#
#
# Custom plotting with matplotlib

import matplotlib.patches as patches
import matplotlib.pyplot as plt

from SecretPlots.objects.shapes import *


class Bar:
    def __init__(self, start, value,
                 thickness=0.8,
                 baseline=0.0,
                 align="center",
                 shape="rect",
                 axis="x",
                 **kwargs):
        self._start = start
        self._value = value
        self._thickness = thickness
        self._baseline = baseline
        self._align = align
        self._shape = shape
        self._axis = axis
        self._options = kwargs

    @property
    def start(self):
        return self._start

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val

    @property
    def thickness(self):
        return self._thickness

    @property
    def align(self):
        return self._align

    @property
    def baseline(self):
        return self._baseline

    @baseline.setter
    def baseline(self, value):
        self._baseline = value

    @property
    def axis(self):
        return self._axis

    @property
    def shape(self):
        if self._shape == "rect":
            return Rectangle
        elif self._shape == "tri":
            return Triangle
        elif self._shape == "diam":
            return Diamond
        else:
            raise Exception("Unknown Shape {}".format(self._shape))

    def set_orientation(self, value):
        self._axis = value

    def set_shape(self, shape):
        self._shape = shape

    def add_option(self, key, value):
        self._options[key] = value

    @property
    def path(self):
        correction = 0
        if self.align == "center":
            correction = self.thickness / 2

        loc = (self.start - correction, self.baseline)
        if self.axis == "y":
            loc = (self.baseline, self.start - correction)

        return self.shape(loc, self.value, self.thickness, self.axis,
                          **self._options).path


class Axis:
    def __init__(self,
                 items,
                 orientation="x",
                 xlim=None,
                 ylim=None):
        self.items = items
        self.orientation = orientation
        self._ticks = []
        self._values = []
        self._labels = []
        self._xlim = xlim
        self._ylim = ylim

    @property
    def ticks(self):
        return self._ticks

    @property
    def values(self):
        return self._values

    @property
    def labels(self):
        if len(self._labels) == 0:
            self._labels = ["{}".format(x) for x in range(len(self.items))]
        return self._labels

    def _add_to_axis(self, item: Bar):
        self._ticks.append(item.start)
        self._values.append(item.value + item.baseline)

    def _prepare(self):

        for m in self.items:
            self._add_to_axis(m)
            m.set_orientation(self.orientation)

    def _draw_bars(self, ax):
        for p in self.items:
            pp = patches.PathPatch(p.path)
            ax.add_patch(pp)

    def _calculate_limit(self):
        loc = (min(self.ticks) - 1, 1 + max(self.ticks))
        val = (min(self.values) - 1, 1 + max(self.values))
        if self.orientation == "x":
            if self._xlim is None:
                self._xlim = loc
            if self._ylim is None:
                self._ylim = val
        else:
            if self._ylim is None:
                self._ylim = loc
            if self._xlim is None:
                self._xlim = val

    def _draw_axis(self, ax):

        if self._xlim is None or self._ylim is None:
            self._calculate_limit()

        if self._xlim is not None:
            ax.set_xlim(self._xlim)

        if self._ylim is not None:
            ax.set_ylim(self._ylim)

    def _draw_ticks(self, ax):
        if self.orientation == "x":
            ax.set_xticks(self.ticks)
            ax.set_xticklabels(self.labels)
        else:
            ax.set_yticks(self.ticks)
            ax.set_yticklabels(self.labels)

    def draw(self, ax):
        self._prepare()
        self._draw_bars(ax)
        self._draw_axis(ax)
        self._draw_ticks(ax)


class Assemble:
    def __init__(self, pyplot, axis, rows=None, cols=None):
        self.plt = pyplot
        self._axis = axis
        self._drawing_axis = []
        self.rows = rows or 1
        self.cols = cols or 1
        self._fig = None

    @property
    def fig(self):
        if self._fig is None:
            self._fig = plt.figure()
        return self._fig

    def _make_grid(self):
        for i in range(len(self._axis)):
            self._drawing_axis.append(self.fig.add_subplot(self.rows,
                                                           self.cols,
                                                           i + 1))

    def _draw_all(self):
        for x in range(len(self._axis)):
            self._axis[x].draw(self._drawing_axis[x])

    def draw(self):
        self._make_grid()
        self._draw_all()
        self.plt.show()


def test():
    orientation = "y"
    b = Bar(0, 5)
    b2 = Bar(1, 3)
    a = Axis([b, b2], orientation=orientation)
    k = Assemble(plt, [a])
    k.draw()


def run():
    test()
