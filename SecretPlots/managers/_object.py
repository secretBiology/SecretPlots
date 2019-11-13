#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 8:09 PM
#
# Object Manager

import numpy as np

from SecretPlots.constants import *
from SecretPlots.managers._axis import AxisManager
from SecretPlots.managers._color import ColorManager
from SecretPlots.objects import Element
from SecretPlots.utils import Log


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
        self._missing_options = None
        self.shape = "r"
        self.max_x = 0
        self.max_y = 0
        self.min_x = 0
        self.min_y = 0
        self.show_missing = True
        self._no_of_missing = 0
        self._log.info("ObjectManager is initialized with default values")

    @property
    def options(self):
        if self._options is None:
            self._options = {}
        return self._options

    @property
    def missing_options(self):
        if self._missing_options is None:
            self._missing_options = {
                "fill": False,
                "hatch": "//",
                "zorder": 0
            }
        return self._missing_options

    def add_options(self, **kwargs):
        self._options = {**self.options, **kwargs}

    def add_missing_options(self, **kwargs):
        self._missing_options = {**self.missing_options, **kwargs}

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

        if np.isnan(value):
            self._no_of_missing += 1
            value = 0
        else:
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

    def _get_network_object(self, x, y, value, pos):
        e = Element(self._log)
        e.add_options(**self.options)
        e.width = self.width
        e.height = self.height
        e.add_options(color=self.cm.color(pos, value))
        self._check_limits(x - e.width / 2, y - e.height / 2)
        self._check_limits(x + e.width / 2, y + e.height / 2)
        return e.get(x - e.width / 2, y - e.height / 2)

    def _get_colormap_object(self, x, y, value, pos):
        e = Element(self._log)
        if np.isnan(value):
            self._no_of_missing += 1
            e.add_options(**self.missing_options)
        else:
            e.add_options(**self.options)
        e.add_options(color=self.cm.color(pos, value))
        e.shape = self.shape
        e.width = self.width
        e.height = self.height
        self._check_limits(x, y)
        self._check_limits(x + e.width, y + e.height)
        return e.get(x, y)

    def get(self, x, y, value, pos):
        if self.cm.plot_type in [PLOT_BAR, PLOT_STACKED_BAR, PLOT_GROUPED_BAR]:
            return self._get_bar_object(x, y, value, pos)
        elif self.cm.plot_type in [PLOT_COLOR_MAP, PLOT_BOOLEAN_PLOT]:
            return self._get_colormap_object(x, y, value, pos)
        elif self.cm.plot_type in [PLOT_NETWORK]:
            return self._get_network_object(x, y, value, pos)
        else:
            self._log.error("ObjectManager for {} is not set".format(
                self.cm.plot_type))
