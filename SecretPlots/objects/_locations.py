#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 03/10/19, 2:59 PM
#
# All Location Managers will go here

import numpy as np

from SecretPlots.constants.graph import *
from SecretPlots.objects._managers import AxisManager
from SecretPlots.objects.base2 import Data
from SecretPlots.utils import Log


class LocationManager:
    def __init__(self, am: AxisManager, log: Log):
        self._log = log
        self._major = None
        self._minor = None
        self.width = 1
        self.height = 1
        self.start_point = (0, 0)
        self.am = am

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


class BarLocations(LocationManager):

    @property
    def plot_type(self):
        return PLOT_BAR

    def validate(self, data: Data):
        self._log.info("Valid data is provided for the BarPlot")
        return True

    def _simple_bars(self, data: Data):
        self._log.info("Calculating positions for simple Bars")
        points = []
        for loc in data.positions:
            points.append((
                self.major + loc[1] * (self.width + self.major_gap),
                self.minor
            ))
        return points

    def _stacked_bars(self, data: Data):
        self._log.info("Calculating positions for Stacked Bars")
        points = []
        stack = None
        last_col = 0
        for loc, value in zip(data.positions, data.value):
            m1, m2 = loc
            if stack is None:
                stack = self.minor
            if m1 != last_col:
                stack = self.minor
                last_col += 1

            points.append((
                self.major + m1 * (self.width + self.major_gap),
                stack
            ))
            stack += value + self.minor_gap
        return points

    def get(self, data: Data) -> list:
        self.validate(data)

        if data.type in [Data.SINGLE_VALUED, Data.SIMPLE_CATEGORICAL]:
            return self._simple_bars(data)
        elif data.type in [Data.COMPLEX_CATEGORICAL, Data.MATRIX]:
            return self._stacked_bars(data)
        elif data.type == Data.POINTS:
            if data.is_single_point:
                return self._simple_bars(data)
            else:
                return self._stacked_bars(data)
        else:
            self._log.error("This data type is nor supported for BarPlot")


class ColorMapLocations(LocationManager):

    @property
    def plot_type(self):
        return PLOT_COLOR_MAP

    def validate(self, data: Data):
        if data.type == Data.COMPLEX_CATEGORICAL:
            self._log.error("Invalid data type for ColorMap")
        self._log.info("Valid data is provided for the ColorMap")
        return True

    def _bars(self, data: Data):
        self._log.info("Calculating positions for ColorMap")
        points = []
        stack = None
        last_col = 0
        for loc in data.positions:
            m1, m2 = loc
            if stack is None:
                stack = self.minor
            if m1 != last_col:
                stack = self.minor
                last_col += 1

            points.append((
                self.major + m1 * (self.width + self.major_gap),
                stack
            ))
            stack += self.height + self.minor_gap
        return points

    def get(self, data: Data) -> list:
        self.validate(data)
        return self._bars(data)


class HistLocations(LocationManager):

    @property
    def plot_type(self):
        return PLOT_HIST

    def __init__(self, am: AxisManager, log: Log, bins=None):
        super().__init__(am, log)
        if bins is None:
            bins = "autp"
        self.bins = bins
        self._hist_options = {}

    def validate(self, data: Data):
        if data.type != Data.SIMPLE_CATEGORICAL:
            self._log.warn("Data will be flatten for histogram")
        self._log.info("Valid data is provided for Histogram")

    def get(self, data: Data):
        self.validate(data)

        bins, _ = np.histogram(data.value, self.bins, **self._hist_options)
        return [(self.major + x * (self.width + self.major_gap), self.minor)
                for x in range(len(bins))]

    def hist_options(self, **kwargs):
        self._hist_options = {**self._hist_options, **kwargs}


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
