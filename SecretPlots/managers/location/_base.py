#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:52 PM
#
# All Location Managers will go here

from SecretPlots.managers._axis import AxisManager
from SecretPlots.managers._object import ObjectManager
from SecretPlots.objects import Data
from SecretPlots.utils import Log


class LocationManager:
    def __init__(self, am: AxisManager, om: ObjectManager, log: Log):
        self._log = log
        self._major = None
        self._minor = None
        self.om = om
        self.start_point = (0, 0)
        self.am = am

    @property
    def width(self):
        return self.om.width

    @property
    def height(self):
        return self.om.height

    @property
    def major_gap(self):
        return self.am.major.gap

    @property
    def minor_gap(self):
        return self.am.minor.gap

    @property
    def plot_type(self):
        raise NotImplementedError

    @property
    def major(self):
        if self._major is None:
            self._major, self._minor = self.start_point
        return self._major

    @property
    def minor(self):
        if self._minor is None:
            self._major, self._minor = self.start_point
        return self._minor

    def validate(self, data: Data):
        raise NotImplementedError

    def get(self, data: Data):
        raise NotImplementedError
