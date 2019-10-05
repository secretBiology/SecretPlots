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
        if log is None:
            log = Log()
        self._log = log
        self._assembler = None

        self.assembler.data = data
        self._log.info(
            "'{}' initialization complete ".format(self.assembler.type))

    @property
    def main_assembler(self) -> Assembler:
        raise NotImplementedError

    @property
    def assembler(self):
        if self._assembler is None:
            self._assembler = self.main_assembler
        return self._assembler

    def show(self):
        self.assembler.draw()
        plt.show()
