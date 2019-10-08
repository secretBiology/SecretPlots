#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:53 PM
#
#
# Matrix Locators

from SecretPlots.constants.graph import *
from SecretPlots.managers.location._base import LocationManager
from SecretPlots.objects import Data


class ColorMapLocations(LocationManager):

    @property
    def plot_type(self):
        return PLOT_COLOR_MAP

    def validate(self, data: Data):
        self._log.info("Data validated fo ColorMap")
        return True

    def _single_column(self, data: Data):

        self._log.info("Calculating positions for simple Bars")
        points = []
        for loc in data.positions:
            points.append((
                self.major,
                self.minor + loc[1] * (self.height + self.minor_gap)
            ))
        return points

    def _matrix_columns(self, data: Data):
        points = []
        for loc in data.positions:
            row, col = loc
            points.append((
                self.major + row * (self.width + self.major_gap),
                self.minor + col * (self.height + self.minor_gap)
            ))
        return points

    def _complex_columns(self, data: Data):
        points = []
        stack = None
        col_no = 0
        for loc in data.positions:
            row, col = loc
            if stack is None:
                stack = self.minor
            if col_no != row:
                stack = self.minor
                col_no = row
            points.append((
                self.major + row * (self.width + self.major_gap),
                stack
            ))
            stack += self.height + self.minor_gap

        return points

    def get(self, data: Data):
        self.validate(data)
        if data.type in [Data.SINGLE_VALUED, Data.SIMPLE_CATEGORICAL]:
            return self._single_column(data)
        elif data.type in [Data.POINTS, Data.MATRIX]:
            return self._matrix_columns(data)
        elif data.type == Data.COMPLEX_CATEGORICAL:
            return self._complex_columns(data)
        else:
            self._log.error("Data type {} does not support ColorMap".format(
                data.type_name))
