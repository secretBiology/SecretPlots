#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:52 PM
#
# Bar Locations

import numpy as np

from SecretPlots.constants import *
from SecretPlots.managers._axis import AxisManager
from SecretPlots.managers.location._base import LocationManager
from SecretPlots.objects import Data
from SecretPlots.utils import Log


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
            if np.isnan(value):
                value = 0
                self._log.warn("NaN value found, ignoring its effect")
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


class BarGroupLocations(LocationManager):

    def __init__(self, am: AxisManager, om, log: Log):
        super().__init__(am, om, log)
        self.group_gap = am.group_gap

    @property
    def plot_type(self):
        return PLOT_GROUPED_BAR

    def validate(self, data: Data):
        self._log.info("Data validated fo GroupedBarPlot")
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

    def _grouped_bars(self, data: Data):
        self._log.info("Calculating positions for Grouped Bars")
        points = []
        bars = -1
        for loc, value in zip(data.positions, data.value):
            m1, m2 = loc
            bars += 1
            points.append((
                self.major + bars * (self.width + self.major_gap) +
                m1 * self.group_gap,
                self.minor
            ))
        return points

    def get(self, data: Data) -> list:
        self.validate(data)

        if data.type in [Data.SINGLE_VALUED, Data.SIMPLE_CATEGORICAL]:
            return self._simple_bars(data)
        elif data.type in [Data.COMPLEX_CATEGORICAL, Data.MATRIX]:
            return self._grouped_bars(data)
        elif data.type == Data.POINTS:
            if data.is_single_point:
                return self._simple_bars(data)
            else:
                return self._grouped_bars(data)
        else:
            self._log.error("This data type is nor supported for "
                            "GroupedBarPlot")


class HistLocations(LocationManager):

    @property
    def plot_type(self):
        return PLOT_HIST

    def __init__(self, am: AxisManager, om, log: Log, bins=None):
        super().__init__(am, om, log)
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
