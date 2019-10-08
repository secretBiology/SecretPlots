#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:47 PM
#
#
#  Matrix Assemblers

from SecretPlots.assemblers import Assembler
from SecretPlots.constants import *
from SecretPlots.managers import ColorMapLocations


class ColorMapAssembler(Assembler):

    @property
    def main_location_manager(self):
        return ColorMapLocations(self.am, self.om, self._log)

    @property
    def type(self):
        return PLOT_COLOR_MAP

    def _adjust_defaults(self):

        if self.type != PLOT_BOOLEAN_PLOT:
            if self.gm.has_colorbar is None:
                self.gm.has_colorbar = True
            if self.gm.colorbar_location is None:
                self.gm.colorbar_location = "right"
            else:
                if self.gm.has_colorbar is None:
                    self.gm.has_colorbar = True

        else:
            self.em.show_legends = True

    def _draw_elements(self):
        locations = self.lm.get(self.data)
        for loc, val, pos in zip(locations, self.data.value,
                                 self.data.positions):
            x, y = loc
            if self.am.orientation == "y":
                x, y = y, x

            if self.type == PLOT_BOOLEAN_PLOT:
                if self.data.threshold is None:
                    self._log.error("For BooleanPlot, you should specify "
                                    "threshold")
                v = 1 if val >= self.data.threshold else 0
                shape = self.om.get(x, y, v, pos)
            else:
                shape = self.om.get(x, y, val / self.data.max, pos)

            self.ax.add_patch(shape.get())
            self.em.draw_values(shape, val,
                                self.cm.color(pos, val / self.data.max))

        ticks_major = []
        ticks_minor = []
        edge_major = []
        edge_minor = []
        for i, m in enumerate(locations):
            if i == 0:
                edge_major.append(m[0])
                edge_minor.append(m[1])
            elif i == len(locations) - 1:
                edge_major.append(m[0] + self.om.width)
                edge_minor.append(m[1] + self.om.height)
            temp = round(m[0] + self.om.width / 2, 2)
            temp_minor = round(m[1] + self.om.height / 2, 2)
            if temp not in ticks_major:
                ticks_major.append(temp)
            if temp_minor not in ticks_minor:
                ticks_minor.append(temp_minor)

        self.am.major.make_ticks(ticks_major)
        self.am.minor.make_ticks(ticks_minor)
        self.am.major.edgelines = edge_major
        self.am.minor.edgelines = edge_minor

        self.am.major.make_labels()
        self.am.minor.make_labels()

    def draw(self):
        self._adjust_defaults()
        self._draw_elements()
        self._draw_axis()
        self._draw_extra()


class BooleanAssembler(ColorMapAssembler):

    @property
    def type(self):
        return PLOT_BOOLEAN_PLOT
