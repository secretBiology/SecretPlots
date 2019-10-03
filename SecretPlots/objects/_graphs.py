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

from SecretPlots.objects._managers import *
from SecretPlots.objects.shapes import *


class BarManager(PlotManager):

    @property
    def type(self):
        return PLOT_BAR

    @property
    def lm(self):
        return BarLocations(self._log)

    def draw(self, ax: plt.Axes):
        self.am.major.gap = 0.5
        self.am.minor.gap = 0.5
        pos = self.am.get_locations(self.lm, self.data)
        for loc, value in zip(pos, self.data.value):
            ax.add_patch(Rectangle(loc[0], loc[1], self.am.width, value).get())

        ax.set_xlim(self.am.x.limit)
        ax.set_ylim(0, max(self.data.value) + 1)
        ax.set_xticks(self.am.x.ticks)


class BarPlot:
    def __init__(self, data, fig: plt.Figure = None):
        self.data = data
        if fig is None:
            fig = plt.figure()
        self.fig = fig
        self.manager = BarManager()
        self.manager.add_data(data)

    def show(self):
        ax = self.fig.add_subplot(111)
        self.manager.draw(ax)
        plt.show()


def run():
    data = [2, 4]
    b = BarPlot(data)
    b.show()
