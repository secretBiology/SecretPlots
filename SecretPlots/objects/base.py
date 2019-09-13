#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 12/09/19, 9:54 AM
#
#
#  Base object for all the plotting


import matplotlib
import matplotlib.pylab as plt
from SecretColors import Palette, ColorMap

from SecretPlots.utils import calculate_dimensions


class Base:
    def __init__(self, data):
        self.p = plt
        self.palette = Palette()
        self.cmap = ColorMap(matplotlib, self.palette)
        self.__data = data
        self.__no_of_samples, self.__no_of_groups = calculate_dimensions(data)

    @property
    def data(self):
        return self.__data

    @property
    def no_of_samples(self):
        return self.__no_of_samples

    @property
    def no_of_groups(self):
        return self.__no_of_groups

    def show(self):
        raise NotImplementedError()

    def tight(self, **kwargs):
        self.p.tight_layout(**kwargs)
