#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 8:03 PM
#
#
# Grid Manager

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from SecretPlots.utils import Log


class GridManager:
    def __init__(self, fig: plt.Figure, log: Log):
        self.fig = fig
        self._log = log
        self._log.info("GridManager is initialized with default values")
        self._main = None
        self._cb = None
        self.has_colorbar = None
        self._cb_location = None
        self._ax_grid = None

    @property
    def colorbar_location(self):
        if self._cb_location is None:
            self._cb_location = "right"
        return self._cb_location

    @colorbar_location.setter
    def colorbar_location(self, value):
        self._cb_location = value

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

    def _generate_axes(self):
        if not self.has_colorbar:
            self._main = self.fig.add_subplot(111)
            self._log.info("Plot Grid is set to normal.")
            return

        if self._cb_location in ["right", "r"]:
            main = self.ax_grid[:, :-1]
            cb = self.ax_grid[:, -1]
        elif self._cb_location in ["left", "l"]:
            main = self.ax_grid[:, 1:]
            cb = self.ax_grid[:, 0]
        elif self._cb_location in ["top", "t"]:
            main = self.ax_grid[1:, :]
            cb = self.ax_grid[0, :]
        elif self._cb_location in ["bottom", "b"]:
            main = self.ax_grid[:-1, :]
            cb = self.ax_grid[-1, :]
        else:
            self._log.error("No such colorbar location found : {}".format(
                self._cb_location))

        self._main = self.fig.add_subplot(main)
        self._cb = self.fig.add_subplot(cb)
        self._log.info("Plot Grid is set according to colorbar location")

    def get_main_axis(self) -> plt.Axes:
        if self._main is None:
            self._generate_axes()
        return self._main

    def get_colorbar_axis(self) -> plt.Axes:
        if self._main is None:
            self._generate_axes()
        return self._cb
