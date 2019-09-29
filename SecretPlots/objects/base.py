#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 27/09/19, 10:40 PM
#
#
#

import itertools
import logging

from SecretColors.utils import text_color, rgb_to_hex

from SecretPlots.objects.shapes import *


class Log:
    def __init__(self, show_log: bool = False,
                 raise_error: bool = False,
                 options: dict = None,
                 add_to_console: bool = True,
                 add_to_file: bool = False,
                 filename: str = "script.log",
                 logging_format: str = "%(asctime)s %(filename)s : %(message)s"):
        self.show_log = show_log
        self.formatter = logging.Formatter(logging_format)
        self.add_to_console = add_to_console
        self.add_to_file = add_to_file
        self.filename = filename
        self._log_object = None

    @property
    def log_object(self):
        if self._log_object is None:
            self._log_object = logging.getLogger("log")
            if self.add_to_console:
                console = logging.StreamHandler()
                console.setFormatter(self.formatter)
                self._log_object.addHandler(console)

            if self.add_to_file:
                log_file = logging.FileHandler(self.filename)
                log_file.setFormatter(self.formatter)
                self._log_object.addHandler(log_file)
        return self._log_object

    def info(self, message):
        if self.show_log:
            self.log_object.setLevel(logging.INFO)
            self.log_object.info(message)

    def error(self, message, raise_exception=True):
        if self.show_log:
            self.log_object.setLevel(logging.ERROR)
            self.log_object.error(message)

        if raise_exception:
            raise Exception(message)

    def warn(self, message):
        if self.show_log:
            self.log_object.setLevel(logging.WARN)
            self.log_object.warning(message)


class Element:
    def __init__(self, _log: Log):
        self._log = _log
        self.x = None
        self.y = None
        self.width = 1
        self.height = 1
        self.rotation = 0
        self._options = None
        self._shape = "rectangle"

    @property
    def options(self):
        if self._options is None:
            self._options = {}
        return self._options

    def add_options(self, **kwargs):
        self._options = {**self.options, **kwargs}

    @property
    def shape(self):
        if self._shape.strip().lower() in ["r", "rectangle", "rect"]:
            return Rectangle(self.x, self.y, self.width, self.height,
                             self.rotation, **self.options)
        elif self._shape.strip().lower() in ["t", "triangle", "tri"]:
            return Triangle(self.x, self.y, self.width, self.height,
                            self.rotation, **self.options)
        elif self._shape.strip().lower() in ["c", "circle", "cir"]:
            return Circle(self.x, self.y, self.width, self.height,
                          self.rotation, **self.options)
        else:
            raise Exception("No such shape found : {}".format(self._shape))

    @shape.setter
    def shape(self, value):
        self._shape = value


class AxisAttributes:
    def __init__(self, name, _log: Log):
        self._log = _log
        self.name = name
        self.gap = 0
        self.show_ticks = True
        self.show_ticks_labels = True
        self.show_midlines = False
        self.is_inverted = False
        self._ticks = None
        self._ticks_direction = None
        self._ticks_labels = None
        self._midlines_options = None
        self._ticks_options = None
        self._labels_options = None
        self._padding = None

    @property
    def ticks(self):
        if self._ticks is None:
            return []
        return self._ticks

    @ticks.setter
    def ticks(self, values):
        if not values:
            self.show_ticks = False
        self._ticks = values

    @property
    def midline_options(self):
        if self._midlines_options is None:
            self._midlines_options = {}
        return self._midlines_options

    @property
    def ticks_labels(self):
        if self._ticks_labels is None:
            if len(self.ticks) == 0:
                return []
            else:
                self._ticks_labels = ["{}".format(round(x, 2)) for x in
                                      self.ticks]
        return self._ticks_labels

    @ticks_labels.setter
    def ticks_labels(self, values):
        self._ticks_labels = values

    @property
    def padding(self):
        if self._padding is None:
            self._padding = (1, 1)
        return self._padding

    @padding.setter
    def padding(self, value):
        try:
            if len(value) == 2:
                self._padding = value
        except TypeError:
            self._log.warn("Both start and end padding set as {}. You "
                           "can provide padding as (start, end) for "
                           "more fine tuned values".format(value))
            self._padding = (value, value)

    def add_midlines(self, **kwargs):
        self.show_midlines = True
        self._midlines_options = {**self.midline_options, **kwargs}

    def add_ticks(self, ticks, **kwargs):
        self._ticks = ticks
        self._ticks_options = kwargs

    def add_ticks_labels(self, labels, **kwargs):
        self._ticks_labels = labels
        self._labels_options = kwargs


class Data:
    def __init__(self, value, _log: Log, threshold=None):
        self._log = _log
        self._raw_value = value
        self._value = None
        self._rows = None
        self._columns = None
        self._is_matrix = None
        self._threshold = threshold

    def _set_value(self, value):
        if self._threshold is None:
            self._value = value
        else:
            self._log.info("Threshold data with {}".format(self._threshold))
            try:
                value = np.ma.array(value, mask=np.isnan(value))
                value = np.where(value < self._threshold, 0, value)
                value = np.where(value >= self._threshold, 1, value)
                self._value = value
            except TypeError:
                self._log.warn("Given data is either not iterable or single")
                if value < self._threshold:
                    self._value = 0
                else:
                    self._value = 1

    def _assign_single_value(self, value):
        self._log.info("Assigning single value")
        self._set_value(value)
        self._rows = 1
        self._columns = 1
        self._is_matrix = False

    def _format_values(self):
        try:
            iter(self._raw_value)
            # This is part of iterator, check dimensions
            self._check_iterator()
        except TypeError:
            # This is single value
            self._assign_single_value(self._raw_value)

    def _check_iterator(self):
        if len(self._raw_value) == 1:
            self._log.warn("Data has only one element in its iterator")
            self._assign_shape(self._raw_value[0])
        else:
            self._assign_shape(self._raw_value)

    def _assign_shape(self, values):

        # Here important to add try and catch, else the _check_iterator box
        # will catch this
        values = np.asarray(values)
        try:
            values = list(itertools.zip_longest(*values, fillvalue=np.NaN))
            values = np.asarray(values).T
        except TypeError:
            self._log.warn("Returning single iterator")

        if len(values.shape) == 0:
            # Again just a single value
            self._assign_single_value(values)
        elif len(values.shape) == 1:
            # Single list or array
            self._set_value(values)
            self._rows = len(values)
            self._columns = 1
            self._is_matrix = False
        else:
            self._log.info("Regular data matrix found")
            # Proper Matrix
            self._set_value(values)
            self._rows = values.shape[0]
            self._columns = values.shape[1]
            self._is_matrix = True

    @property
    def is_matrix(self):
        if self._is_matrix is None:
            self._format_values()
        return self._is_matrix

    @property
    def rows(self):
        if self._rows is None:
            self._format_values()
        return self._rows

    @property
    def columns(self):
        if self._columns is None:
            self._format_values()
        return self._columns

    @property
    def value(self):
        if self._value is None:
            self._format_values()
        return self._value


class Section:
    def __init__(self, data, _log: Log):
        self._log = _log
        self._raw_data = data
        self._data = Data(data, self._log)
        self._section_gap = 1
        self._missing_data = None
        self._true_data = []

    @property
    def data(self):
        return self._data

    @property
    def missing_data(self):
        if self._missing_data is None:
            self._true_data = [x for x in self.sequence if not np.isnan(x)]
            self._missing_data = len(self.sequence) > len(self._true_data)
        return self._missing_data

    @property
    def sequence(self):
        try:
            return self.data.value.flatten()
        except AttributeError:
            self._log.warn("Data can not be flatten. Most likely single "
                           "valued")
            return [self.data.value]

    @property
    def section_gap(self):
        return self._section_gap

    @section_gap.setter
    def section_gap(self, value):
        self._section_gap = value

    @property
    def max(self):
        if self.missing_data:
            return np.amax(self._true_data)
        return np.amax(self._data.value)

    @property
    def min(self):
        if self.missing_data:
            return np.amin(self._true_data)
        return np.amin(self._data.value)

    @property
    def rows(self):
        return self._data.rows

    @property
    def columns(self):
        return self._data.columns

    @property
    def no_of_elements(self):
        try:
            return self._data.value.size
        except AttributeError:
            self._log.warn("Data size can not be determined. Most likely due "
                           "to single value")
            return 1

    def add_threshold(self, value):
        self._log.info("New threshold of {} is set".format(value))
        self._data = Data(self._raw_data, self._log, threshold=value)


class AxisManager:
    def __init__(self, x: AxisAttributes, y: AxisAttributes, _log: Log):
        self._log = _log
        self._x = x
        self._y = y
        self._orientation = "x"

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, value):
        self._log.info("Orientation changed to {}".format(value))
        self._orientation = value

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
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def get_positions(self, section: Section, x, y, width, height):

        def _row(index):
            return int(index / section.columns)

        def _column(index):
            return index % section.columns

        def _loc(r, c):
            x_pos = x + c * width + c * self.x.gap
            y_pos = y + r * height + r * self.y.gap
            if self.orientation == "y":
                x_pos = x + r * width + r * self.x.gap
                y_pos = y + c * height + c * self.y.gap
            return x_pos, y_pos

        pos = []
        for i in range(len(section.sequence)):
            pos.append(_loc(_row(i), _column(i)))

        boundary_x = pos[-1][0]
        boundary_y = pos[-1][1]

        if self.orientation == "x":
            boundary_x += section.section_gap + width
            boundary_y = y
        else:
            boundary_x = x
            boundary_y += section.section_gap + height

        return pos, (boundary_x, boundary_y)

    def swap_axis(self, padding_changed: bool):

        if self.orientation == "x":
            self.orientation = "y"
            self._log.info("Major axis swapped to y")
        else:
            self.orientation = "x"
            self._log.info("Major axis swapped to x")

        # If user has not changed padding
        if not padding_changed:
            if self.orientation == "x":
                self.padding(1, 1, 0, 1)
            else:
                self.padding(0, 1, 1, 1)

    def padding(self, start, end=None, bottom=None, top=None):
        if [end, bottom, top].count(None) == 3:
            end, bottom, top = start, start, start
            self._log.info("Automatic padding of {} is assigned to all "
                           "axis".format(start))

        if end is None:
            end = self.x.padding[1]
            self._log.info("Setting end padding to {}".format(end))
        if bottom is None:
            bottom = self.y.padding[0]
            self._log.info("Setting bottom padding to {}".format(bottom))
        if top is None:
            top = self.y.padding[1]
            self._log.info("Setting top padding to {}".format(top))

        self.x.padding = (start, end)
        self.y.padding = (bottom, top)


class Assembler:
    def __init__(self, fig: plt.Figure, _log: Log):
        self._log = _log
        self.fig = fig
        self.sections = []
        self.width = 1
        self.height = 1
        self.section_gap = 1
        self.section_boundary = False
        self.show_missing = False

        self._fig_drawn = False
        self._ax_grid = None
        self._base_ax = None
        self._palette = None
        self._text = False
        self._text_options = None
        self._section_boundary_options = None
        self._am = AxisManager(
            AxisAttributes("x", self._log), AxisAttributes("y", self._log),
            self._log)
        self._log.info("Default AxisAttributes were used for assembler")

    @property
    def am(self):
        return self._am

    @property
    def text_options(self):
        if self._text_options is None:
            self._text_options = {}
        return self._text_options

    @property
    def palette(self) -> Palette:
        if self._palette is None:
            self._palette = Palette(show_warning=False)
        return self._palette

    @palette.setter
    def palette(self, value: Palette):
        self._log.info("Default palette changed to {}".format(value.name))
        self._palette = value

    @property
    def ax_grid(self):
        raise NotImplementedError("Provide GridSpec properties")

    @property
    def ax(self):
        raise NotImplementedError("Provide main figure axes")

    def draw(self):
        raise NotImplementedError("Draw method is mandatory")

    @property
    def section_boundary_options(self):
        if self._section_boundary_options is None:
            self._section_boundary_options = {
                "color": self.palette.gray(shade=30),
                "alpha": 0.5,
                "zorder": 0,
            }
        return self._section_boundary_options

    def _add_text(self, shape, text, rgba_color):

        r, g, b, _ = rgba_color

        opts = {"ha": "center",
                "color": text_color(rgb_to_hex(r, g, b))
                }

        opts = {**opts, **self.text_options}

        x = shape.x + self.width * opts["anchor"][0]
        y = shape.y + self.height * opts["anchor"][1]

        if opts["anchor"][0] != 0.5 and opts["anchor"][1] != 0.5:
            del opts["ha"]

        del opts["anchor"]

        self.ax.text(x, y,
                     "{}".format(round(text, 2)),
                     **opts)

    def add_text_options(self, **kwargs):
        self._text_options = {**self.text_options, **kwargs}

    def show(self, tight=False):
        if self._fig_drawn:
            self._log.warn("Figure is already drawn, hence skipping")
        else:
            self.draw()
        if tight:
            self._log.info("Generating tight layout")
            plt.tight_layout()
        plt.show()

    def add_section(self, data, gap=None):
        s = Section(data, self._log)
        if gap is not None:
            s.section_gap = gap
        self.sections.append(s)
        self._log.info(
            "New section with gap {} is added".format(s.section_gap))

    def add_x_midlines(self, **kwargs):
        self.am.x.add_midlines(**kwargs)

    def add_y_lines(self, **kwargs):
        self.am.y.add_midlines(**kwargs)

    def add_midlines(self, **kwargs):
        self.am.x.add_midlines(**kwargs)
        self.am.y.add_midlines(**kwargs)

    def add_xgap(self, value):
        self.am.x.gap = value

    def add_ygap(self, value):
        self.am.y.gap = value

    def add_gap(self, value):
        self.am.x.gap = value
        self.am.y.gap = value

    def add_section_boundary(self, **kwargs):
        self.section_boundary = True
        self._section_boundary_options = {**self.section_boundary_options,
                                          **kwargs}

    def invert_x_axis(self):
        self.am.x.is_inverted = True

    def invert_y_axis(self):
        self.am.y.is_inverted = True


def run():
    data = [np.random.uniform(0, 10, 2) for x in range(2)]

    fig = plt.figure()
    # a = Assembler(fig)
    # a.add_section(data)
