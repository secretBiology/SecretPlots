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

    @property
    def thickness(self):
        return self._thickness

    @property
    def align(self):
        return self._align

    @property
    def baseline(self):
        return self._baseline

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


def test():
    fig = plt.figure()
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    b = Bar(2, 1, baseline=3.2, axis="x", cut_position="b", shape="tri")
    b2 = Bar(2, 3, axis="x", cut_position="t", cut_outward=False)
    p = patches.PathPatch(b.path)
    p2 = patches.PathPatch(b2.path)
    ax.set(xlim=(0, 5), ylim=(-1, 5))
    ax.add_patch(p)
    ax.add_patch(p2)
    ax.axhline(0)
    ax.axvline(0)
    ax.axvline(4)
    plt.show()


def run():
    test()
