#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 30/09/19, 10:11 AM
#
#
# All managers

from SecretPlots.objects.base2 import *
from SecretPlots.utils import Log


class PlotManager:
    BAR = "bar"

    def __init__(self, log: Log = None):
        if log is None:
            log = Log()
        self._log = log
        self._type = None
        self._data = None
        self._lm = None

    @property
    def lm(self):
        if self._lm is None:
            self._lm = LocationManager(self._log)
        return self._lm

    @property
    def type(self):
        if self._type is None:
            self._log.error("Plot type should be defined")
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def data(self) -> Data:
        return self._data

    @data.setter
    def data(self, value):
        self._data = Data(value, self._log)

    def add_data(self, data):
        self.data = data
        return self

    def add_type(self, value: str):
        self.type = value
        return self


class LocationManager:
    def __init__(self, log: Log):
        self.log = log
        self.orientation = "x"
        self.plot_type = None

    def x_function(self):
        raise NotImplementedError

    def y_function(self):
        raise NotImplementedError


class BarLocations(LocationManager):

    def __init__(self, log: Log):
        super().__init__(log)
        self.width = None
        self.height = None
        self.x_gap = None
        self.y_gap = None

    def x_function(self):
        pass

    def y_function(self):
        pass


class AxisManager:
    def __init__(self, log):
        self._log = log
        self.orientation = "x"


def run():
    import numpy as np
    data = np.random.rand(1, 5)
    p = PlotManager()
    p.add_data(data)
    p.add_type("bar")

    print(p.data)
