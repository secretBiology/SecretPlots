#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 12/09/19, 9:54 AM
#
#
#  Base object for all the plotting

import copy

import matplotlib
import matplotlib.pylab as plt
from SecretColors import Palette
from matplotlib.patches import Patch

DEFAULT_MISSING = {
    "fill": False,
    "hatch": "//"
}


class GroupObject:
    def __init__(self,
                 colors: list = None,
                 group_labels: list = None,
                 gap: float = 0.5):
        self._groups = []
        self.palette = Palette()
        self._gap = gap
        self._colors = colors
        self.show_missing = False
        self._group_labels = group_labels

    @property
    def gap(self):
        return self._gap

    @property
    def size(self):
        return len(self.groups)

    @property
    def non_null_size(self):
        return len([x for x in self.groups if not x.is_null])

    @property
    def first_non_null(self):
        for g in self.groups:
            if g.allowed(self.show_missing):
                return g
        raise Exception("At least one Non-None value should be there in the "
                        "Group")

    @property
    def last_non_null(self):
        for g in reversed(self.groups):
            if g.allowed(self.show_missing):
                return g
        raise Exception("At least one Non-None value should be there in the "
                        "Group")

    @property
    def tick_position(self):
        if self.size == 0:
            self.__error()
        elif self.size == 1:
            return self.groups[0].position
        else:
            return self.first_non_null.position + (
                    self.last_non_null.position -
                    self.first_non_null.position) / 2

    @property
    def groups(self):
        return self._groups

    @property
    def no_of_missing(self):
        return len([x for x in self.groups if x.is_null])

    @property
    def boundary(self):
        if self.size == 0:
            self.__error()
        elif self.size == 1:
            p1 = self.groups[0]
            if p1.is_center_aligned:
                return p1.position - p1.width / 2, p1.position + p1.width / 2
            else:
                return p1.position, p1.position + p1.width
        else:
            p1 = self.groups[0]
            p2 = self.groups[-1]
            left = p1.position
            if p1.is_center_aligned:
                left = p1.position - p1.width / 2
            right = p2.position
            if p2.is_center_aligned:
                right = p2.position + p2.width / 2
            return left, right

    def __error(self):
        raise Exception("This group is empty.")

    def __assign_color(self, group_pos):
        if self._colors is None:
            if self.size > len(self.palette.get_color_list):
                c = self.palette.random(no_of_colors=(self.size + 1))
            else:
                c = self.palette.get_color_list[:(self.size + 1)]

            return c[group_pos]

        else:
            if len(self._colors) == 1:
                return self._colors
            else:
                return self._colors[group_pos]

    def add_group(self, obj):
        n = copy.deepcopy(obj)
        if n.color is None:
            n.color = self.__assign_color(len(self.groups))
        self._groups.append(n)

    def get_group_dict(self):
        k = {}
        for g in self.groups:
            if not g.is_null:
                k[g.color] = g
        return k

    def reset_colors(self, function):
        for b in self.groups:
            b.color = next(function)


class BarObject:
    def __init__(self, value: float, margin_next: float = 0.2, **kwargs):

        self._value = value
        self._margin_next = margin_next
        self.palette = Palette()
        self._options = kwargs
        self._position = None

        if "align" not in kwargs.keys():
            self._options["align"] = "center"

    @property
    def value(self):
        return self._value

    @property
    def is_center_aligned(self):
        return self._options["align"] == "center"

    @property
    def margin_next(self):
        return self._margin_next

    @property
    def width(self):
        if "width" in self.options.keys():
            return self.options["width"]
        else:
            return 0.8

    @property
    def is_null(self):
        return self.value is None

    @property
    def color(self):
        try:
            return self.options["color"]
        except KeyError:
            return None

    @color.setter
    def color(self, value):
        self.options["color"] = value

    @property
    def options(self):
        return self._options

    @property
    def position(self):
        if self._position is None:
            raise Exception(
                "Bar position will assigned only by axis. Please use this "
                "property in axis")
        else:
            return self._position

    @position.setter
    def position(self, pos: float):
        self._position = pos

    @property
    def tick_position(self):
        if self.is_center_aligned:
            return self.position
        else:
            return self.position + self.width / 2

    @property
    def label(self):
        try:
            return self.options["label"]
        except KeyError:
            return None

    def allowed(self, show_missing):
        return self.value is not None or show_missing


class AxisObject:
    def __init__(self,
                 axis: str,
                 samples: list,
                 labels: list = None,
                 show_missing: bool = False,
                 **kwargs):

        self._samples = []
        self._axis = axis
        self._labels = labels
        self._options = kwargs
        self.start_point = 0

        self._show_missing = show_missing
        self._original_samples = self._convert(samples)
        self._last_value = self.start_point

        self._flatten_samples(self._original_samples)

    @staticmethod
    def _convert(samples):
        if all(type(x) == BarObject for x in samples):
            return samples
        else:
            k = []
            for x in samples:
                if type(x) == BarObject:
                    g = GroupObject()
                    g.add_group(x)
                    k.append(g)
                elif type(x) == GroupObject:
                    k.append(x)
                else:
                    raise Exception("Object {} not supported".format(type(x)))
            return k

    @property
    def show_missing(self):
        return self._show_missing

    @show_missing.setter
    def show_missing(self, value):
        self._show_missing = value
        self._samples = []
        self._flatten_samples(self._original_samples)

    @property
    def axis(self):
        return self._axis

    @property
    def last_value(self):
        return self._last_value

    @property
    def x(self):
        return self.axis.strip().lower() == "x"

    @property
    def samples(self):
        return self._samples

    @property
    def labels(self):
        if self._labels is None:
            self._labels = ["{}".format(x + 1) for x in range(len(
                self.samples))]

        return self._labels

    @property
    def ticks(self):
        out = []
        for x in self.samples:
            out.append(x.tick_position)
        return out

    @property
    def all_groups(self):
        for s in self.samples:
            if type(s) == BarObject:
                if s.allowed(self.show_missing):
                    g = GroupObject()
                    g.add_group(s)
                    yield g
            else:
                yield s

    def _flatten_samples(self, sam):
        self._samples = []
        for s in sam:
            if type(s) == BarObject:
                if s.allowed(self.show_missing):
                    self._samples.append(s)
            elif type(s) == GroupObject:
                if s.non_null_size > 0 or self.show_missing:
                    s.show_missing = self.show_missing
                    self._samples.append(s)
            else:
                raise Exception("Unknown format {} for flattening "
                                "samples".format(type(s)))

    def __update_last(self, bar: BarObject):
        bar.position = self._last_value
        self._last_value += bar.width + bar.margin_next

    def __update_group(self, g: GroupObject):
        self._last_value += g.gap

    def swap_axis(self):
        if self._axis == "x":
            self._axis = "y"
        else:
            self._axis = "x"

    def reversed(self):
        self._samples = [x for x in reversed(self._samples)]

    def arrange(self):
        out = []
        self._last_value = self.start_point
        for x in self.samples:
            if type(x) == BarObject:
                pos = self.last_value
                self.__update_last(x)
                out.append((pos, x))
            elif type(x) == GroupObject:
                for g in x.groups:
                    if g.allowed(self.show_missing):
                        pos = self.last_value
                        self.__update_last(g)
                        out.append((pos, g))
                self.__update_group(x)
            else:
                raise Exception("Unknown group object: {}".format(type(x)))

        return out

    def set_ticks(self, p: matplotlib.pylab):
        if self.x:
            p.xticks(self.ticks, self.labels)
        else:
            p.yticks(self.ticks, self.labels)

    def get_legends_dict(self):
        temp = {}
        for g in self.all_groups:
            temp = {**temp, **g.get_group_dict()}
        return temp

    def missing_values(self):
        c = 0
        for g in self.all_groups:
            c += g.no_of_missing
        return c


class LegendsObject:
    def __init__(self, legends: dict, options, show_missing,
                 missing_options, no_of_missing):
        self.legends = legends
        self.show_missing = show_missing
        self.missing_options = missing_options
        self.options = options
        self.no_of_missing = no_of_missing

    def get_legend_patches(self):
        patches = []
        counter = 1
        for g in self.legends:
            label = self.legends[g].label
            if label is None:
                label = "Group {}".format(counter)
                counter += 1
            patches.append(Patch(
                facecolor=g,
                label=label
            ))

        if self.show_missing and self.no_of_missing > 0:
            opts = {**DEFAULT_MISSING}
            if self.missing_options is not None:
                opts = {**opts, **self.missing_options}
            patches.append(Patch(**opts))
        return patches

    def add_legend(self, p: matplotlib.pylab, **kwargs):
        if len(kwargs) == 0:
            kwargs["bbox_to_anchor"] = (1, 1)
        kwargs["handles"] = self.get_legend_patches()
        p.legend(**kwargs)


class Assembler:
    def __init__(self, axis: AxisObject,
                 p: matplotlib.pylab,
                 show_boundaries=False,
                 boundaries_options=None,
                 show_missing=False,
                 missing_options=None,
                 show_legends=False,
                 legends_options=None
                 ):
        self.palette = Palette()
        self.plt = p
        self._show_boundaries = show_boundaries
        self._boundaries_options = boundaries_options
        self._show_missing = show_missing
        self._missing_options = missing_options
        self._show_legends = show_legends
        self._legends_options = legends_options
        self._last_color = -1
        self.axis = axis

    def _draw_boundaries(self):
        if not self._show_boundaries:
            return
        opts = {
            "color": self.palette.gray(shade=30),
            "alpha": 0.5,
            "zorder": 0,
        }

        opts = {**opts, **self._boundaries_options}

        ob = self.plt.axhspan
        if self.axis.x:
            ob = self.plt.axvspan

        for g in self.axis.all_groups:
            b1, b2 = g.boundary
            ob(b1, b2, **opts)

    def _handle_missing(self, pos: float, bar: BarObject):
        if not self._show_missing:
            return
        opts = {**DEFAULT_MISSING}

        opts = {**opts, **self._missing_options}

        ob = self.plt.axhspan
        if self.axis.x:
            ob = self.plt.axvspan

        if bar.is_center_aligned:
            ob(pos - bar.width / 2, pos + bar.width / 2, **opts)
        else:
            ob(pos, pos + bar.width, **opts)

    def _assign_color(self):
        try:
            self._last_color += 1
            return self.palette.get_color_list[self._last_color]
        except IndexError:
            return self.palette.random()

    def _draw(self, pos, b: BarObject):
        if "color" not in b.options.keys():
            b.options["color"] = self._assign_color()
        if self.axis.x:
            self.plt.bar(pos, b.value, **b.options)
        else:
            self.plt.barh(pos, b.value, **b.options)

    def _draw_legends(self):
        if not self._show_legends:
            return

        gd = self.axis.get_legends_dict()

        legends = LegendsObject(gd,
                                self._legends_options,
                                self._show_missing,
                                self._missing_options,
                                self.axis.missing_values())
        legends.add_legend(self.plt, **self._legends_options)

    def _generate(self):
        # This is important to use arrange first so that all locations will
        # be recorded in given object instances

        for b1 in self.axis.arrange():
            pos, b = b1
            if b.is_null:
                self._handle_missing(pos, b)
                continue
            self._draw(pos, b)

        # Following after positions are fixed
        self._draw_boundaries()
        self.axis.set_ticks(self.plt)
        self._draw_legends()

    def add_boundaries(self, **kwargs):
        self._show_boundaries = True
        if self._boundaries_options is None:
            self._boundaries_options = {}
        self._boundaries_options = {**self._boundaries_options, **kwargs}

    def add_missing(self, **kwargs):
        self.axis.show_missing = True
        self._show_missing = True
        if self._missing_options is None:
            self._missing_options = {}
        self._missing_options = {**self._missing_options, **kwargs}

    def add_legends(self, **kwargs):
        self._show_legends = True
        if self._legends_options is None:
            self._legends_options = {}
        self._legends_options = {**self._legends_options, **kwargs}

    def add_colors(self, colors: list):
        if type(colors) != list:
            colors = [colors]

        def __color_cycle():
            while True:
                for c in colors:
                    yield c

        k = __color_cycle()
        for s in self.axis.samples:
            if type(s) == BarObject:
                s.color = next(k)
            elif type(s) == GroupObject:
                t = __color_cycle()
                s.reset_colors(t)

    def swap_axis(self):
        self.axis.swap_axis()

    def reversed(self):
        self.axis.reversed()

    def show(self):
        self._generate()
        self.plt.show()


def run():
    b1 = BarObject(3)
    b2 = BarObject(5)
    e = BarObject(None)
    g = GroupObject()
    g.add_group(b2)
    g.add_group(b1)
    g.add_group(e)
    g2 = GroupObject()
    g2.add_group(b2)
    g2.add_group(e)
    g2.add_group(b1)

    x1 = AxisObject("x", [b1, b2])
    a = Assembler(x1, plt)
    a.show()
