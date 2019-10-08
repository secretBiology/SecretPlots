#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 03/10/19, 3:57 PM
#
#
# All graph managers

import matplotlib.pyplot as plt

from SecretPlots.managers import *
from SecretPlots.objects import Data
from SecretPlots.utils import Log


class Assembler:

    def __init__(self, fig: plt.Figure, log: Log):
        self._log = log
        self._fig = fig

        self._type = None
        self._data = None
        self._am = None
        self._lm = None
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

        if self.am.x.scale is not None:
            self.ax.set_xscale(self.am.x.scale)
        if self.am.y.scale is not None:
            self.ax.set_yscale(self.am.y.scale)

    def _draw_axis(self):
        self._set_auto_limit()
        if len(self.am.x.ticks) != 0:
            self.ax.set_xticks(self.am.x.ticks)
            self.ax.set_xticklabels(self.am.x.tick_labels)
        if len(self.am.y.ticks) != 0:
            self.ax.set_yticks(self.am.y.ticks)
            self.ax.set_yticklabels(self.am.y.tick_labels)

        left, right, top, bottom = self.am.frame_visibility
        self.ax.spines['left'].set_visible(left)
        self.ax.spines['right'].set_visible(right)
        self.ax.spines['top'].set_visible(top)
        self.ax.spines['bottom'].set_visible(bottom)

        if self.am.aspect_ratio is not None:
            self.ax.set_aspect(self.am.aspect_ratio)

        self._check_axis_transformations()

    def _draw_extra(self):
        self.am.major.make_midlines()
        self.am.minor.make_midlines()

        self.em.draw_midlines()
        self.em.draw_edgelines()
        self.em.draw_colorbar(self.data)
        self.em.draw_legends()


def run():
    data = [[3, 4, 1], [1, 3], 2]
