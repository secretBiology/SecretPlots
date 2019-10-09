#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 29/09/19, 11:39 PM
#
#
# Basic Objects

from SecretPlots.objects.shapes import *
from SecretPlots.utils import Log


class Data:
    """
    Class to hold and transform data

    Following are the data types

    0: Single Valued
    Only single not iterable number
    e.g. 1, 23, -8

    1: Points
    Iterable with exactly two length
    if sub-iterators, they should have same length
    e.g. [1,2] , [[1,1], [2,2]]

    2: Simple Categorical
    Iterator with length more than 2 with no sub-iterators
    e.g. [1,2,3,4]

    3: Matrix
    Iterator with sub-iterators with same length (and are not points)
    e.g. [[1,1,1], [2,2,2]]

    4: Complex Categorical
    Iterator with sub-iterators with uneven length
    e.g. [[1,1], [2,2,2], [3,3,3]], [[1,2,3,4]]

    Currently more than 2 Dimensions are not supported. So you should
    convert multidimensional data into 2D to fit into this framework

    """
    SINGLE_VALUED = 0
    POINTS = 1
    SIMPLE_CATEGORICAL = 2
    MATRIX = 3
    COMPLEX_CATEGORICAL = 4

    def __init__(self, data, log: Log):
        self._raw_data = data
        self._log = log
        self._type = None
        self._value = None
        self._positions = None
        self.threshold = None

    @property
    def max(self):
        return np.nanmax(self.value)

    @property
    def min(self):
        return np.nanmin(self.value)

    @property
    def value(self):
        """
        Flatten values of the entire dataset

        Argument 'dtype=np.float' is required for replacement of None
        """
        if self._value is None:
            if self.type != Data.COMPLEX_CATEGORICAL:
                self._value = np.asarray(self._raw_data,
                                         dtype=np.float).flatten()
            else:
                self._value = []
                for k in self._raw_data:
                    try:
                        self._value.extend(np.asarray(k))
                    except TypeError:
                        self._value.append(k)
                self._value = np.asarray(self._value, dtype=np.float)
        return self._value

    @property
    def positions(self):
        """
        Returns flatten array of positions of the (row, column) in given
        dataset
        """
        if self._positions is None:
            if self.type == Data.SINGLE_VALUED:
                self._positions = [(0, 0)]
            elif self.type == Data.POINTS:
                self._assign_point_locations()
            elif self.type == Data.SIMPLE_CATEGORICAL:
                self._positions = [(0, x) for x in range(len(self._raw_data))]
            elif self.type == Data.MATRIX:
                self._positions = []
                row, cols = np.asarray(self._raw_data).shape
                for r in range(row):
                    for c in range(cols):
                        self._positions.append((r, c))
            elif self.type == Data.COMPLEX_CATEGORICAL:
                self._assign_complex_locations()

            self._log.info("Locations assigned to the data points")

        return self._positions

    @property
    def type(self) -> int:
        if self._type is None:
            self._assign_type()
        return self._type

    @property
    def type_name(self) -> str:
        if self.type == Data.SINGLE_VALUED:
            return "Single Valued"
        elif self.type == Data.POINTS:
            return "Points"
        elif self.type == Data.SIMPLE_CATEGORICAL:
            return "Simple Categorical"
        elif self.type == Data.COMPLEX_CATEGORICAL:
            return "Complex Categorical"
        elif self.type == Data.MATRIX:
            return "Matrix"
        else:
            self._log.error("No such category found {}".format(self.type))

    @property
    def raw_data(self):
        return self._raw_data

    @property
    def is_single_point(self) -> bool:
        if self.type != Data.POINTS:
            return False
        else:
            try:
                iter(self.raw_data[0])
                return False
            except TypeError:
                return True

    def _assign_point_locations(self):
        self._positions = []
        for i, x in enumerate(self._raw_data):
            try:
                iter(x)
                for k in range(len(x)):
                    self.positions.append((i, k))
            except TypeError:
                self.positions.append((0, i))

    def _assign_complex_locations(self):
        self._positions = []
        for i, x in enumerate(self._raw_data):
            try:
                for j, k in enumerate(x):
                    self._positions.append((i, j))
            except TypeError:
                self._log.warn("Non-iterable element ({}) found in the "
                               "Complex Categorical dataset".format(x))
                self._positions.append((i, 0))

    def _assign_type(self):
        try:
            iter(self._raw_data)
            try:
                self._check_multi_dimension()
            except TypeError:
                self._log.error("Something went wrong in calculating "
                                " data dimensions. Please check input data.")
        except TypeError:
            # Single Valued
            self._type = Data.SINGLE_VALUED
            self._log.info("Data type assigned as Single Valued ({})".format(
                Data.SINGLE_VALUED))

    def _check_multi_dimension(self):
        temp = [np.asarray(m) for m in self._raw_data]
        temp_len = [m.size for m in temp]
        if len(temp) == 2 and temp_len.count(temp_len[0]) == len(temp_len):
            # Points
            self._type = Data.POINTS
        else:
            if temp_len.count(temp_len[0]) == len(temp_len) and len(
                    temp_len) != 1:

                if temp_len[0] == 1:
                    self._type = Data.SIMPLE_CATEGORICAL
                else:
                    self._type = Data.MATRIX
            else:
                self._type = Data.COMPLEX_CATEGORICAL

        self._log.info("Data type assigned as {} ({})".format(self.type,
                                                              self.type_name))


class Element:
    def __init__(self, log):
        self._log = log
        self.is_point = False
        self.width = 1
        self.height = 1
        self.value = None
        self.rotation = 0
        self._options = None
        self._shape = "r"

    @property
    def shape(self):
        if self._shape in ["r", "rectangle", "rect"]:
            return Rectangle
        elif self._shape in ["t", "triangle", "tri"]:
            return Triangle
        elif self._shape in ["c", "circle", "cir"]:
            return Circle
        else:
            self._log.error("Shape {} not found".format(self._shape))

    @shape.setter
    def shape(self, value: str):
        self._shape = value.strip().lower()

    @property
    def options(self):
        if self._options is None:
            self._options = {}
        return self._options

    def add_options(self, **kwargs):
        self._options = {**self.options, **kwargs}

    def get(self, x, y):
        return self.shape(x, y, self.width, self.height, self.rotation,
                          **self.options)


class Axis:
    def __init__(self, name: str, index: int, log: Log):
        self.name = name
        self.index = index
        self._log = log
        self.show_ticks = True
        self._ticks = None
        self._tick_labels = None
        self._ticklabels_options = None
        self._tick_directions = None
        self._tick_options = None
        self._gap = None
        self._gap_options = None
        self._user_defined_gap = False
        self.show_midlines = False
        self.show_edgelines = False
        self._midlines_options = None
        self._midlines = None
        self._edgelines_options = None
        self._edgelines = None
        self._label = None
        self._label_options = None

        self.scale = None
        self.limit = (0, 1)
        self.padding_start = None
        self.padding_end = None
        self.is_inverted = False
        self._missing_region = []

        self._log.info("{} axis instance is generated".format(name))

    @property
    def ticks(self) -> list:
        if self._ticks is None:
            self._ticks = []
        return self._ticks

    @ticks.setter
    def ticks(self, values):
        self._ticks = values

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = value

    @property
    def missing_regions(self):
        return self._missing_region

    @property
    def midlines(self):
        return self._midlines

    @property
    def edgelines(self):
        if self._edgelines is None:
            self._edgelines = []
        return self._edgelines

    @midlines.setter
    def midlines(self, values):
        self._midlines = values

    @edgelines.setter
    def edgelines(self, values):
        self._edgelines = values

    @property
    def label_options(self):
        if self._label_options is None:
            self._label_options = {}
        return self._label_options

    @property
    def midlines_options(self):
        if self._midlines_options is None:
            self._midlines_options = {}
        return self._midlines_options

    @property
    def edgelines_options(self):
        if self._edgelines_options is None:
            self._edgelines_options = {}
        return self._edgelines_options

    @property
    def ticklabels_options(self):
        if self._ticklabels_options is None:
            self._ticklabels_options = {}
        return self._ticklabels_options

    @property
    def tick_options(self):
        if self._tick_options is None:
            self._tick_options = {}
        return self._tick_options

    @property
    def tick_labels(self) -> list:
        if self._tick_labels is None:
            self._tick_labels = []
        return self._tick_labels

    @tick_labels.setter
    def tick_labels(self, values):
        self._tick_labels = values

    @property
    def gap(self) -> float:
        if self._gap is None:
            self._gap = 0
        return self._gap

    @gap.setter
    def gap(self, value: float):
        self._user_defined_gap = True
        self._gap = value

    @property
    def is_user_defined_gap(self):
        return self._user_defined_gap

    def add_midlines_options(self, **kwargs):
        self._midlines_options = {**self.midlines_options, **kwargs}

    def add_edgelines_options(self, **kwargs):
        self._edgelines_options = {**self.edgelines_options, **kwargs}

    def add_ticklabels_options(self, **kwargs):
        self._ticklabels_options = {**self.ticklabels_options, **kwargs}

    def add_tick_options(self, **kwargs):
        self._tick_options = {**self.tick_options, **kwargs}

    def add_label_options(self, **kwargs):
        self._label_options = {**self.label_options, **kwargs}

    def add_missing_region(self, p1, length):
        self._missing_region.append((p1, p1 + length))

    def make_ticks(self, values):
        if self._ticks is not None:
            self._log.info("Ticks for {} have already been set by "
                           "user".format(self.name))
            return
        self._ticks = values
        self._log.info("Ticks for {} automatically set".format(self.name))

    def make_labels(self):
        if self._tick_labels is not None:
            self._log.info("Tick labels for {} are already defined".format(
                self.name))
            return
        self._tick_labels = ["{}".format(x) for x in range(len(self.ticks))]
        self._log.info("{} tick_labels automatically generated".format(
            self.name))

    def make_midlines(self):
        if self.midlines is not None:
            self._log.info("Generation of midlines ignored because they are "
                           "already generated")
            return

        self._midlines = []
        if len(self.ticks) == 1:
            self._log.warn("{} midlines could not be generated because only "
                           "1 bar is present".format(self.name))
            return

        for i, x in enumerate(self.ticks[:-1]):
            self._midlines.append((x + self.ticks[i + 1]) / 2)
        self._log.info("{} midlines automatically generated".format(self.name))


def run():
    pass
