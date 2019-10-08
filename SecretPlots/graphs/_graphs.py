#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:57 PM
#
#
#
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 11:03 AM
#
#
# Main graph class

import matplotlib.pyplot as plt

from SecretPlots.assemblers import Assembler
from SecretPlots.utils import Log


class SecretPlot:
    def __init__(self, data, fig: plt.Figure = None, log: Log = None):
        if fig is None:
            fig = plt.figure()
        self.fig = fig
        self._raw_data = data
        if log is None:
            log = Log(show_log=True)
        self._log = log
        self._assembler = None
        self.orientation = None
        self.x_gap = None
        self.y_gap = None
        self.group_gap = None
        self.colors = None
        self.cmap = None
        self.cmap_location = None
        self.show_cmap = None
        self.show_legend = None

        self._log.info(
            "'{}' initialization complete ".format(self.assembler.type))

    def _check_settings(self):
        if self.orientation is not None:
            self.assembler.am.orientation = self.orientation
        if self.x_gap is not None:
            self.x.gap = self.x_gap
        if self.y_gap is not None:
            self.y.gap = self.y_gap
        if self.group_gap is not None:
            self.assembler.am.group_gap = self.group_gap
        if self.colors is not None:
            self.assembler.cm.user_colors = self.colors
        if self.cmap is not None:
            self.assembler.cm.user_cmap = self.cmap

        self.assembler.gm.has_colorbar = self.show_cmap
        self.assembler.gm.colorbar_location = self.cmap_location
        self.assembler.em.show_legends = self.show_legend

    @property
    def main_assembler(self) -> Assembler:
        raise NotImplementedError

    @property
    def x(self):
        return self.assembler.am.x

    @property
    def y(self):
        return self.assembler.am.y

    @property
    def ax(self):
        return self.assembler.am.ax

    @property
    def assembler(self):
        if self._assembler is None:
            self._assembler = self.main_assembler
            self._assembler.data = self._raw_data
        return self._assembler

    def _assemble_components(self):
        self._check_settings()
        self.assembler.draw()

    def show(self):
        self._assemble_components()
        plt.show()
