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


def run():
    data = [1, 2, 3]
    h = ColorPlot(data)
    h.show()
