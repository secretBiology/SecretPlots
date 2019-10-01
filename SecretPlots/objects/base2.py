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

from SecretPlots.objects.managers import *
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

    @property
    def type(self):
        if self._type is None:
            self._assign_type()
        return self._type

    @property
    def type_name(self):
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
        self.shape = "r"

    @property
    def options(self):
        if self._options is None:
            self._options = {}
        return self._options

    def add_options(self, **kwargs):
        self._options = {**self.options, **kwargs}




def run():
    pass
