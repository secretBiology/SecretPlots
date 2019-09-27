#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 26/09/19, 11:38 AM
#
#
# Base objects

import numpy as np

SINGLE_VALUE = 0
MATRIX_2d_VALUE = 1


class Data:
    def __init__(self, values, logger=None):
        self._raw_data = values
        self._logger = logger

    def type(self):
        raise NotImplementedError("Data subclass should implement data type")

    @property
    def is_single_valued(self):
        return self.type() == SINGLE_VALUE

    @property
    def rows(self):
        raise NotImplementedError("No of rows should be provided")

    @property
    def columns(self):
        raise NotImplementedError("No of columns should be provided")

    @property
    def value(self):
        raise NotImplementedError("Data should be provided")


class Single(Data):

    def __init__(self, values, logger=None):
        super().__init__(values, logger)

    def type(self):
        return SINGLE_VALUE

    @property
    def rows(self):
        return 1

    @property
    def columns(self):
        return 1

    @property
    def value(self):
        return self._raw_data


class Matrix2D(Data):

    def __init__(self, values, logger=None):
        super().__init__(values, logger)
        self._data = None

    def _format_data(self):
        if self._data is None:
            if len(self._raw_data) == 1:
                try:
                    iter(self._raw_data[0])
                    self._data = np.asarray(self._raw_data[0])
                except TypeError:
                    self._data = np.asarray(self._raw_data)
            else:
                self._data = np.asarray(self._raw_data)

    def type(self):
        return MATRIX_2d_VALUE

    @property
    def rows(self):
        if len(self.value.shape) == 1:
            return len(self.value)
        elif len(self.value.shape) == 2:
            return self.value.shape[1]
        else:
            raise Exception("Matrix2D only accepts 2D data")

    @property
    def columns(self):
        if len(self.value.shape) == 1:
            return 1
        elif len(self.value.shape) == 2:
            return self.value.shape[0]
        else:
            raise Exception("Matrix2D only accepts 2D data")

    @property
    def value(self):
        if self._data is None:
            self._format_data()
        return self._data


class Section:
    def __init__(self, margin: float = 1):
        self._data = []
        self.margin = margin
        self._max = 0
        self._min = 0

    def _assign_data(self, data):
        try:
            iter(data)
            m = Matrix2D(data)
            self._max = np.amax(m.value)
            self._min = np.amin(m.value)
            return m
        except TypeError:
            self._max = data
            self._min = data
            return Single(data)

    def add_data(self, data):
        self._data.append(self._assign_data(data))

    @property
    def data(self):
        return self._data

    @property
    def max(self):
        return self._max

    @property
    def min(self):
        return self._min


class CategoryPlot:
    def __init__(self):
        self._orientation = None
        self.x_gap = 0
        self.y_gap = 0
        self.x_padding = (1, 1)
        self.y_padding = (1, 0)
        self._padding_defined = False
        self.x_lines = False
        self.y_lines = False
        self._sections = []
        self.x_fills = []
        self.y_fills = []
        self.x_ticks = None
        self.y_ticks = None
        self.x_labels = None
        self.y_labels = None
        self._x_label_options = None
        self._y_label_options = None
        self._x_ticks_options = None
        self._y_ticks_options = None
        self._x_lines_options = None
        self._y_lines_options = None
        self._x_gap_options = None
        self._y_gap_options = None
        self._x_fills_options = None
        self._y_fills_options = None
        self._background_options = None
        self._text_options = None
        self._shape_options = None

    def add_section(self, section: Section):
        self._sections.append(section)

    def add_x_fill(self, xfill):
        self.x_fills.append(xfill)

    def add_y_fill(self, yfill):
        self.y_fills.append(yfill)

    def check_labels(self, major, minor):
        x = major
        y = minor

        if self.orientation == "y":
            x, y = y, x

        if self.x_labels is None:
            self.x_labels = x

        if self.y_labels is None:
            self.y_labels = y

    @property
    def orientation(self):
        if self._orientation is None:
            self._orientation = "x"
        return self._orientation

    @orientation.setter
    def orientation(self, value):
        self._orientation = value

    @property
    def x_label_options(self):
        if self._x_label_options is None:
            self._x_label_options = {}
        return self._x_label_options

    @property
    def y_label_options(self):
        if self._y_label_options is None:
            self._y_label_options = {}
        return self._y_label_options

    @property
    def x_ticks_options(self):
        if self._x_ticks_options is None:
            self._x_ticks_options = {}
        return self._x_ticks_options

    @property
    def y_ticks_options(self):
        if self._y_ticks_options is None:
            self._y_ticks_options = {}
        return self._y_ticks_options

    @property
    def x_gap_options(self):
        if self._x_gap_options is None:
            self._x_gap_options = {}
        return self._x_gap_options

    @property
    def y_gap_options(self):
        if self._y_gap_options is None:
            self._y_gap_options = {}
        return self._y_gap_options

    @property
    def x_fill_options(self):
        if self._x_fills_options is None:
            self._x_fills_options = {}
        return self._x_fills_options

    @property
    def y_fill_options(self):
        if self._y_fills_options is None:
            self._y_fills_options = {}
        return self._y_fills_options

    @property
    def background_options(self):
        if self._background_options is None:
            self._background_options = {}
        return self._background_options

    @property
    def x_lines_options(self):
        if self._x_lines_options is None:
            self._x_lines_options = {}
        return self._x_lines_options

    @property
    def y_lines_options(self):
        if self._y_lines_options is None:
            self._y_lines_options = {}
        return self._y_lines_options

    @property
    def text_options(self):
        if self._text_options is None:
            self._text_options = {}
        return self._text_options

    @property
    def shape_options(self):
        if self._shape_options is None:
            self._shape_options = {}
        return self._shape_options

    def padding(self, start, end=None, top=None, bottom=None):
        if end is None and top is None and bottom is None:
            end, top, bottom = start, start, start
        elif top is None and bottom is None:
            bottom, top = 0, 0
        elif bottom is None:
            bottom = 0
        self.x_padding = (start, end)
        self.y_padding = (top, bottom)
        self._padding_defined = True

    def add_x_label_options(self, **kwargs):
        self._x_label_options = {**self.x_label_options, **kwargs}

    def add_y_label_options(self, **kwargs):
        self._y_label_options = {**self.y_label_options, **kwargs}

    def add_x_gap_options(self, **kwargs):
        self._x_gap_options = {**self.x_gap_options, **kwargs}

    def add_y_gap_options(self, **kwargs):
        self._y_gap_options = {**self.y_gap_options, **kwargs}

    def add_x_fill_options(self, **kwargs):
        self._x_fills_options = {**self.x_fill_options, **kwargs}

    def add_y_fill_options(self, **kwargs):
        self._y_fills_options = {**self.y_fill_options, **kwargs}

    def add_x_lines_options(self, **kwargs):
        self._x_lines_options = {**self.x_lines_options, **kwargs}

    def add_y_lines_options(self, **kwargs):
        self._y_lines_options = {**self.y_lines_options, **kwargs}

    def add_background_options(self, **kwargs):
        self._background_options = {**self.background_options, **kwargs}

    def add_text_options(self, **kwargs):
        self._text_options = {**self.text_options, **kwargs}

    def add_shape_options(self, **kwargs):
        self._shape_options = {**self.shape_options, **kwargs}


def run():
    data = np.random.uniform(0, 100, 10)

    s = Section()
    s.add_data(data)

    print(s.data)
