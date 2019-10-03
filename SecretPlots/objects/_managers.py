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

from SecretPlots.objects._locations import *
from SecretPlots.objects.base2 import *


class PlotManager:

    def __init__(self, log: Log = None):
        if log is None:
            log = Log()
        self._log = log
        self._type = None
        self._data = None
        self._am = None
        self._lm = None

    @property
    def am(self):
        if self._am is None:
            a = AxisManager(self._log)
            a.type = self.type
            self._am = a
        return self._am

    @property
    def type(self):
        raise NotImplementedError

    @property
    def lm(self):
        raise NotImplementedError

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


class AxisManager:
    def __init__(self, log: Log):
        self._log = log
        self.orientation = "x"
        self._x = Axis("x", self._log)
        self._y = Axis("y", self._log)
        self.width = 1
        self.height = 1
        self.type = PLOT_BAR
        self._all_x = None
        self._all_y = None

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def major(self):
        if self.orientation == "x":
            return self._x
        else:
            return self._y

    @property
    def minor(self):
        if self.orientation == "x":
            return self._y
        else:
            return self._x

    @property
    def x_lim(self):
        if self._all_x is None:
            return 1, 1
        else:
            return min(self._all_x) - 1, max(self._all_x) + 1

    def _update_axis(self, info):
        mm = self.width
        n = self.height
        if self.orientation == "y":
            mm = self.height
            n = self.width
        self.major.update([x[0] for x in info], mm)
        self.minor.update([x[1] for x in info], n)

    def get_locations(self, lm: LocationManager, data: Data):
        lm.major_gap = self.major.gap
        lm.minor_gap = self.minor.gap
        lm.start_point = (0, 0)
        lm.width = self.width
        lm.height = self.height
        locs = lm.get(data)
        self._update_axis(locs)
        return locs


def run():
    data = np.random.uniform(1, 3, 10)
