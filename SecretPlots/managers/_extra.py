#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:55 PM
#
#
#
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 30/09/19, 10:11 AM
#
#
# Extra Manager

import matplotlib
import matplotlib.pyplot as plt
from SecretColors.utils import text_color
from matplotlib.patches import Patch

from SecretPlots.managers._axis import AxisManager
from SecretPlots.managers._color import ColorManager
from SecretPlots.managers._grid import GridManager
from SecretPlots.objects import Data
from SecretPlots.utils import Log


class ExtraManager:
    def __init__(self, gm: GridManager, am: AxisManager, cm: ColorManager,
                 log: Log):
        self.gm = gm
        self.cm = cm
        self.am = am
        self._log = log
        self.show_values = False
        self.show_legends = False
        self._value_options = None
        self._legends_options = None

        self._log.info("ExtraManager is initialized with default values")

    @property
    def value_options(self):
        if self._value_options is None:
            self._value_options = {
                "anchor": (0.5, 0.5),
                "relative": True,
                "offset": (0, 0)
            }
        return self._value_options

    @property
    def legends_options(self):
        if self._legends_options is None:
            self._legends_options = {}
        return self._legends_options

    def add_value_options(self, **kwargs):
        self._value_options = {**self.value_options, **kwargs}

    def add_legends_options(self, **kwargs):
        self._legends_options = {**self.legends_options, **kwargs}

    def draw_values(self, shape, text, bg_color):
        if not self.show_values:
            return

        opts = {"ha": "center", "color": text_color(bg_color)}

        opts = {**opts, **self.value_options}

        if opts["relative"]:
            x = shape.x + shape.width * opts["anchor"][0] + opts["offset"][0]
            y = shape.y + shape.height * opts["anchor"][1] + opts["offset"][1]
        else:
            x = shape.x + opts["anchor"][0] + opts["offset"][0]
            y = shape.y + opts["anchor"][1] + opts["offset"][1]

        if opts["anchor"][0] != 0.5 and opts["anchor"][1] != 0.5:
            del opts["ha"]

        del opts["anchor"]
        del opts["relative"]
        del opts["offset"]

        self.gm.get_main_axis(self.cm.plot_type).text(x, y, "{}".format(text),
                                                      **opts)
        self._log.info("Values are shown in the plot")

    def draw_midlines(self):
        if self.am.x.show_midlines:
            for x in self.am.x.midlines:
                self.am.ax.axvline(x, **self.am.x.midlines_options)

        if self.am.y.show_midlines:
            for y in self.am.y.midlines:
                self.am.ax.axhline(y, **self.am.y.midlines_options)

        self._log.info("Midlines are added to the plot")

    def draw_edgelines(self):
        if self.am.x.show_edgelines:
            for x in self.am.x.edgelines:
                self.am.ax.axvline(x, **self.am.x.edgelines_options)

        if self.am.y.show_edgelines:
            for y in self.am.y.edgelines:
                self.am.ax.axhline(y, **self.am.y.edgelines_options)

        self._log.info("Edgelines are added the plot")

    def draw_colorbar(self, data: Data):

        if not self.gm.has_colorbar:
            return

        norm = matplotlib.colors.Normalize(vmin=min(data.value), vmax=max(
            data.value))
        sm = plt.cm.ScalarMappable(cmap=self.cm.cmap, norm=norm)

        if self.gm.colorbar_location in ["right", "left", "r", "l"]:
            ori = "vertical"
        else:
            ori = "horizontal"

        plt.colorbar(sm, cax=self.gm.get_colorbar_axis(self.cm.plot_type),
                     orientation=ori)

        if self.gm.colorbar_location in ["left", "l"]:
            self.gm.get_colorbar_axis(
                self.cm.plot_type).yaxis.set_ticks_position(
                'left')
        elif self.gm.colorbar_location in ["top", "t"]:
            self.gm.get_colorbar_axis(
                self.cm.plot_type).xaxis.set_ticks_position("top")

        self._log.info("Colorbar is added the plot")

    def draw_legends(self):
        if not self.show_legends:
            return

        p = []
        for key in self.cm.all_colors:
            p.append(Patch(
                facecolor=self.cm.all_colors[key],
                label="{}".format(key)
            ))

        opts = {
            "handles": p
        }
        opts = {**opts, **self.legends_options}
        plt.legend(**opts)
        self._log.info("Legends are added to the plot")
