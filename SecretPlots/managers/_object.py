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
        if self.cm.plot_type in [PLOT_BAR, PLOT_STACKED_BAR, PLOT_GROUPED_BAR]:
            return self._get_bar_object(x, y, value, pos)
        elif self.cm.plot_type in [PLOT_COLOR_MAP, PLOT_BOOLEAN_PLOT]:
            return self._get_heatmap_object(x, y, value, pos)
        else:
            self._log.error("ObjectManager for {} is not set".format(
                self.cm.plot_type))
