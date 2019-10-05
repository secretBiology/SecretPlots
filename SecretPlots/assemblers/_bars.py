#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:45 PM
#
#
# Bar Assemblers

from SecretPlots.assemblers._base import Assembler
from SecretPlots.objects._base import Data
from SecretPlots.constants.graph import *


class BarAssembler(Assembler):

    @property
    def type(self):
        if self.data.type in [Data.SINGLE_VALUED, Data.SIMPLE_CATEGORICAL]:
            return PLOT_BAR
        else:
            if self.data.is_single_point:
                return PLOT_BAR
            return PLOT_STACKED_BAR

    @property
    def lm(self):
        return BarLocations(self.am, self._log)

    def _adjust_defaults(self):
        self.am.major.gap = 0.2
        self.am.minor.padding_start = 0

        if self.type == PLOT_STACKED_BAR:
            self.em.show_legends = True

    def _draw_elements(self):
        locations = self.lm.get(self.data)
        for loc, val, pos in zip(locations, self.data.value,
                                 self.data.positions):
            x, y = loc
            if self.am.orientation == "y":
                x, y = y, x

            shape = self.om.get(x, y, val, pos)
            self.ax.add_patch(shape.get())
            self.em.draw_values(shape, val, self.cm.color(pos, val))

        ticks = []
        edge = []
        for i, m in enumerate(locations):
            if i == 0:
                edge.append(m[0])
            elif i == len(locations) - 1:
                edge.append(m[0] + self.om.width)
            temp = round(m[0] + self.om.width / 2, 2)
            if temp not in ticks:
                ticks.append(temp)

        self.am.major.ticks = ticks
        self.am.major.edgelines = edge
        self.am.major.make_labels()  # TODO: Remove if user uses own

    def draw(self):
        self._adjust_defaults()
        self._draw_elements()
        self._draw_axis()
        self._draw_extra()


class BarGroupedAssembler(Assembler):
    @property
    def type(self):
        return PLOT_GROUPED_BAR

    @property
    def lm(self):
        return BarGroupLocations(self.am, self._log, self.am.group_gap)

    def _adjust_defaults(self):
        self.am.major.gap = 0.2
        self.am.minor.padding_start = 0
        self.em.show_legends = True

    def _draw_elements(self):
        locations = self.lm.get(self.data)
        for loc, val, pos in zip(locations, self.data.value,
                                 self.data.positions):
            x, y = loc
            if self.am.orientation == "y":
                x, y = y, x

            shape = self.om.get(x, y, val, pos)
            self.ax.add_patch(shape.get())
            self.em.draw_values(shape, val, self.cm.color(pos, val))

        ticks = []
        edge = []
        current_group = 0
        last_item = None
        for pos, loc in zip(self.data.positions, locations):
            if current_group == pos[0]:
                current_group += 1
                if last_item is not None:
                    edge.append(last_item)
                edge.append(loc)
            last_item = loc
        edge.append(last_item)
        edge = [x[0] for x in edge]
        midlines = []
        for e in range(len(edge)):
            if e % 2 == 1:
                edge[e] += self.om.width
                ticks.append((edge[e - 1] + edge[e]) / 2)
                try:
                    midlines.append((edge[e] + edge[e + 1]) / 2)
                except IndexError:
                    pass

        self.am.major.ticks = ticks
        self.am.major.edgelines = edge
        self.am.major.midlines = midlines

        self.am.major.make_labels()  # TODO: Remove if user uses own

    def draw(self):
        self._adjust_defaults()
        self._draw_elements()
        self._draw_axis()
        self._draw_extra()
