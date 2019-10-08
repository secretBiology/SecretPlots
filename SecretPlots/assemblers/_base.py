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
    def gm(self) -> GridManager:
        if self._gm is None:
            self._gm = GridManager(self._fig, self._log)
        return self._gm

    @property
    def cm(self) -> ColorManager:
        if self._cm is None:
            self._cm = ColorManager(self.type, self._log)
        return self._cm

    @property
    def am(self) -> AxisManager:
        if self._am is None:
            self._am = AxisManager(self.gm, self._log)
        return self._am

    @property
    def om(self) -> ObjectManager:
        if self._om is None:
            self._om = ObjectManager(self.am, self.cm, self._log)
        return self._om

    @property
    def em(self) -> ExtraManager:
        if self._em is None:
            self._em = ExtraManager(self.gm, self.am, self.cm, self._log)
        return self._em

    @property
    def main_location_manager(self) -> LocationManager:
        raise NotImplementedError

    @property
    def lm(self) -> LocationManager:
        if self._lm is None:
            self._lm = self.main_location_manager
        return self._lm

    @property
    def ax(self) -> plt.Axes:
        return self.am.ax

    @property
    def type(self):
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

        if self.am.x.padding_start is None:
            self.am.x.padding_start = 1
        if self.am.y.padding_start is None:
            self.am.y.padding_start = 1
        if self.am.x.padding_end is None:
            self.am.x.padding_end = 1
        if self.am.y.padding_end is None:
            self.am.y.padding_end = 1

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
            self.ax.set_xticks(self.am.x.ticks, **self.am.x.tick_options)
            self.ax.set_xticklabels(self.am.x.tick_labels,
                                    **self.am.x.ticklabels_options)
        if len(self.am.y.ticks) != 0:
            self.ax.set_yticks(self.am.y.ticks, **self.am.y.tick_options)
            self.ax.set_yticklabels(self.am.y.tick_labels,
                                    **self.am.y.ticklabels_options)

        left, right, top, bottom = self.am.frame_visibility
        self.ax.spines['left'].set_visible(left)
        self.ax.spines['right'].set_visible(right)
        self.ax.spines['top'].set_visible(top)
        self.ax.spines['bottom'].set_visible(bottom)

        if self.am.aspect_ratio is not None:
            self.ax.set_aspect(self.am.aspect_ratio)

        if not self.am.x.show_ticks:
            self.ax.set_xticks([])
        if not self.am.y.show_ticks:
            self.ax.set_yticks([])

        if self.am.x.label is not None:
            self.ax.set_xlabel(self.am.x.label, **self.am.x.label_options)
        if self.am.y.label is not None:
            self.ax.set_ylabel(self.am.y.label, **self.am.y.label_options)

        self._check_axis_transformations()

    def _draw_extra(self):
        self.am.major.make_midlines()
        self.am.minor.make_midlines()

        self.em.draw_midlines()
        self.em.draw_edgelines()
        self.em.draw_colorbar(self.data)
        self.em.draw_legends()
        self.em.draw_grid()
        if self.om.show_missing:
            self.em.draw_missing(**self.om.missing_options)


def run():
    data = [[3, 4, 1], [1, 3], 2]
