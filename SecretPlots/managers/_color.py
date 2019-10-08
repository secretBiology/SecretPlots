#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 8:07 PM
#
# Color Manager

import matplotlib
from SecretColors import Palette, ColorMap
from SecretColors.utils import rgb_to_hex

from SecretPlots.constants import *
from SecretPlots.utils import Log


class ColorManager:
    def __init__(self, plot_type: str, log: Log):
        self._log = log
        self.plot_type = plot_type
        self._palette = None
        self._unique_colors = []
        self._all_colors = {}
        self._cmap = None
        self._on_color = None
        self._off_color = None
        self.user_colors = None
        self.user_cmap = None
        self._cycle = None

        self._log.info("ColorManager is initialized with default values.")

    @property
    def on_color(self):
        if self._on_color is None:
            self._on_color = self.palette.blue()
        return self._on_color

    @on_color.setter
    def on_color(self, value):
        self._on_color = value

    @property
    def off_color(self):
        if self._off_color is None:
            self._off_color = self.palette.red()
        return self._off_color

    @off_color.setter
    def off_color(self, value):
        self._off_color = value

    @property
    def palette(self) -> Palette:
        if self._palette is None:
            self._palette = Palette(show_warning=False)
        return self._palette

    @property
    def all_colors(self):
        return self._all_colors

    @property
    def cmap(self):
        if self.user_cmap is not None:
            self._cmap = matplotlib.cm.get_cmap(self.user_cmap)
        if self._cmap is None:
            colors = [self.palette.lime(shade=30), self.palette.lime(),
                      self.palette.brown(shade=40),
                      self.palette.brown(shade=80),
                      self.palette.black()]
            self._cmap = ColorMap(matplotlib, self.palette).from_list(colors)
        return self._cmap

    @staticmethod
    def cycle(color_list):
        while True:
            for c in color_list:
                yield c

    def _get_color(self, index):

        if self.user_colors is not None:
            if self._cycle is None:
                self._cycle = self.cycle(self.user_colors)
            if index not in self._all_colors.keys():
                self._all_colors[index] = next(self._cycle)

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
        if self.plot_type == PLOT_BAR:
            if self.user_colors is not None:
                if len(self.user_colors) > 1:
                    return self._get_color(position[1])
                else:
                    return self._get_color(0)
            return self._get_color(row)
        if self.plot_type in [PLOT_STACKED_BAR, PLOT_GROUPED_BAR]:
            return self._get_color(col)
        elif self.plot_type == PLOT_COLOR_MAP:
            return self._get_from_map(value)
        elif self.plot_type == PLOT_BOOLEAN_PLOT:
            self._all_colors["ON"] = self.on_color
            self._all_colors["OFF"] = self.off_color
            if value == 0:
                return self.off_color
            else:
                return self.on_color
        else:
            return self._get_color(row)
