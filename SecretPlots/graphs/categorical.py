#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 28/09/19, 1:06 AM
#
# All categorical plots

from SecretPlots.assemblers import (Assembler,
                                    BarAssembler,
                                    BooleanAssembler,
                                    BarGroupedAssembler,
                                    ColorMapAssembler)
from SecretPlots.graphs._graphs import SecretPlot


class BarPlot(SecretPlot):

    @property
    def main_assembler(self) -> Assembler:
        return BarAssembler(self.fig, self._log)


class BarGroupedPlot(SecretPlot):

    @property
    def main_assembler(self) -> Assembler:
        return BarGroupedAssembler(self.fig, self._log)


class ColorPlot(SecretPlot):

    @property
    def main_assembler(self) -> Assembler:
        return ColorMapAssembler(self.fig, self._log)


class BooleanPlot(SecretPlot):

    def __init__(self, data, threshold):
        super().__init__(data)
        self.assembler.data.threshold = threshold

    @property
    def main_assembler(self) -> Assembler:
        return BooleanAssembler(self.fig, self._log)


def run():
    data = [6, 3, None, 2]
    h = (ColorPlot(data)
         .add_values()
         .add_y_padding(0, 1)
         .change_orientation("-x")
         .invert_y()
         .add_cmap("Accent", loc="top")
         .show()
         )
