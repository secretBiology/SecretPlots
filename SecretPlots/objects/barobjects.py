#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 14/09/19, 3:58 PM
#
#
# All bar related objects

import matplotlib.pyplot as plt
from SecretColors import Palette
from SecretColors.utils import text_color
from matplotlib.patches import Patch

plt.rcParams.update({'figure.autolayout': True})

DEFAULT_MISSING = {
    "fill": False,
    "hatch": "//",
    "label": "Missing",
    "zorder": 0
}


class ValueObject:
    def __init__(self, value,
                 margin_next: float = 0.2,
                 color=None,
                 **kwargs):
        self._value = value
        self._color = color
        self._margin_next = margin_next
        self._options = kwargs

    @property
    def value(self) -> float:
        return self._value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    @property
    def is_null(self) -> bool:
        return self.value is None

    @property
    def margin_next(self):
        return self._margin_next

    @margin_next.setter
    def margin_next(self, value):
        self._margin_next = value

    @property
    def options(self) -> dict:
        return self._options

    @property
    def width(self):
        try:
            return float(self.options["width"])
        except KeyError:
            return 0.8

    @property
    def align(self):
        try:
            return self.options["align"]
        except KeyError:
            return "center"

    def allowed(self, show_missing: bool) -> bool:
        return show_missing or not self.is_null

    def update_margin(self, value):
        self.margin_next = value

    def update_width(self, value):
        self._options["width"] = value


class GroupObject:
    def __init__(self, items,
                 gap: float = 1,
                 gap_options: dict = None):
        self._items = items
        self._gap = gap
        self._gap_options = gap_options

    @property
    def items(self):
        return self._items

    @property
    def gap(self):
        return self._gap

    @gap.setter
    def gap(self, value):
        self._gap = value

    @property
    def gap_options(self):
        return self._gap_options

    def size(self, show_missing: bool):
        return len([x for x in self.items if x.allowed(show_missing)])

    def update_margin(self, margin):
        for m in self._items:
            m.margin_next = margin

    def update_width(self, value):
        for m in self._items:
            m.update_width(value)


class BarLocations:
    def __init__(self, items,
                 is_stacked: bool,
                 show_missing: bool,
                 start_location: float = 0,
                 start_bottom: float = 0):
        self._original_items = items
        self.show_missing = show_missing
        self._is_stacked = is_stacked
        self._items = []
        self.start_location = start_location
        self.start_bottom = start_bottom
        self._last_location = None

    @property
    def original_items(self):
        return self._original_items

    @property
    def items(self):
        return self._items

    def _add_item(self, item: ValueObject):
        if item.allowed(self.show_missing):
            self._items.append(item)

    def _add_group(self, group: GroupObject):
        self._items.append(group)

    def _flatten_items(self):
        if all([type(x) == ValueObject for x in self.original_items]):
            for f in self.original_items:
                self._add_item(f)
        else:
            for f in self.original_items:
                if type(f) == ValueObject:
                    if f.allowed(self.show_missing):
                        g = GroupObject([f])
                        self._add_group(g)
                elif type(f) == GroupObject:
                    self._add_group(f)
                else:
                    raise Exception("Unknown format {}".format(type(f)))

    def _get_location(self, item: ValueObject):
        if self._last_location is None:
            self._last_location = self.start_location
        loc = self._last_location
        self._last_location += item.width + item.margin_next
        bottom = 0
        return loc, item, bottom

    def _get_stacked_location(self, group: GroupObject):
        if self._last_location is None:
            self._last_location = self.start_location
        out = []
        loc = None
        bottom = None
        last = 0
        for item in group.items:
            if not item.allowed(self.show_missing):
                continue
            if loc is None:
                loc = self._last_location
            if bottom is None:
                bottom = self.start_bottom
            out.append((loc, item, bottom))
            # Save margin to update next sample
            last = item.width + item.margin_next
            # Update bottom for stacked
            if not item.is_null:
                bottom += item.value

        self._last_location += last
        return out

    def _add_gap(self, group: GroupObject, last_margin: float):
        self._last_location += group.gap - last_margin

    def get(self):
        self._flatten_items()
        out = []
        for item in self.items:
            # If these are just simple ValuObjects, just get locations
            if type(item) == ValueObject:
                out.append(self._get_location(item))
            elif type(item) == GroupObject:
                temp_margin = 0
                if self._is_stacked:
                    # Use extend instead append because following will
                    # return list of locations instead single
                    out.extend(self._get_stacked_location(item))
                    # Get extra margin
                    for g in item.items:
                        if g.allowed(self.show_missing):
                            temp_margin = g.margin_next
                else:
                    for g in item.items:
                        if g.allowed(self.show_missing):
                            # Get extra margin
                            temp_margin = g.margin_next
                            out.append(self._get_location(g))
                self._add_gap(item, temp_margin)

        return out


class ColorManager:
    def __init__(self):
        self.palette = Palette()
        self._colors = None
        self._boundaries = None

    @property
    def colors(self):
        if self._colors is None:
            self._colors = self.palette.get_color_list
        return self._colors

    @colors.setter
    def colors(self, vals: list):
        self._colors = vals

    @property
    def boundary(self):
        if self._boundaries is None:
            self._boundaries = self.palette.gray(shade=30)
        return self._boundaries

    @staticmethod
    def _cycle(colors):
        while True:
            for c in colors:
                yield c

    def _color_objects(self, items):
        cor = self._cycle(self.colors)
        for m in items:
            m.color = next(cor)

    def _color_groups(self, items):
        for g in items:
            cor = self._cycle(self.colors)
            if type(g) == ValueObject:
                g.color = next(cor)
            elif type(g) == GroupObject:
                for k in g.items:
                    k.color = next(cor)
            else:
                raise Exception("Unknown Object {}".format(type(g)))

    def update_colors(self, items):
        if all([type(x) == ValueObject for x in items]):
            self._color_objects(items)
        else:
            self._color_groups(items)
        return self


class AxisObject:
    def __init__(self, data,
                 is_stacked: bool,
                 show_missing=None,
                 labels=None):
        self._data = data
        self.show_missing = show_missing
        self.is_stacked = is_stacked
        self._ticks = None
        self._labels = labels
        self._bars = None
        self._boundaries = None

    @property
    def bars(self):
        return self._bars

    @property
    def raw_items(self):
        return [x[1] for x in self.bars]

    @property
    def raw_locations(self):
        return [x[0] for x in self.bars]

    @property
    def ticks(self):
        if self._ticks is None:
            self.calculate_ticks()
        return self._ticks

    @property
    def boundaries(self):
        if self._boundaries is None:
            self.calculate_boundaries()
        return self._boundaries

    @property
    def labels(self):
        if self._labels is None:
            return ["{}".format(x) for x in range(len(self.ticks))]
        else:
            return self._labels

    @staticmethod
    def _get_bounds(loc1: float, start: ValueObject, loc2: float,
                    end: ValueObject):

        if start.align == "center":
            p1 = loc1 - start.width / 2
        else:
            p1 = loc1

        if end.align == "center":
            p2 = loc2 + end.width / 2
        else:
            p2 = loc2 + end.width

        return p1, p2

    def calculate_boundaries(self):
        if self.bars is None:
            self._bars = BarLocations(self._data, self.is_stacked,
                                      self.show_missing).get()

        sizes = []
        for d in self._data:
            if type(d) == ValueObject:
                sizes.append(1)
            elif type(d) == GroupObject:
                sizes.append(d.size(self.show_missing))

        loc = []
        bars = []
        m = self.raw_locations
        b = self.raw_items
        for s in sizes:
            loc.append(m[:s])
            bars.append(b[:s])
            m = m[s:]
            b = b[:s]

        bounds = []
        for i in range(len(loc)):
            if len(loc[i]) == 0:
                continue
            elif len(loc[i]) == 1:
                bounds.append(self._get_bounds(
                    loc[i][0],
                    bars[i][0],
                    loc[i][0],
                    bars[i][0]
                ))
            else:
                bounds.append(self._get_bounds(
                    loc[i][0],
                    bars[i][0],
                    loc[i][-1],
                    bars[i][-1]
                ))

        self._boundaries = bounds

    def calculate_ticks(self):
        if self.bars is None:
            self._bars = BarLocations(self._data,
                                      self.is_stacked,
                                      self.show_missing).get()

        if any([type(x) == ValueObject for x in self._data]):
            self._ticks = self.raw_locations
        else:
            sizes = []
            for d in self._data:
                sizes.append(d.size(self.show_missing))
            loc = []
            m = self.raw_locations
            for s in sizes:
                loc.append(m[:s])
                m = m[s:]

            loc = [sum(x) / len(x) for x in loc]
            self._ticks = loc

    def add_labels(self, labels: list):
        self._labels = labels


class LegendObject:
    def __init__(self, location_data, group_labels=None):
        self.items = [x[1] for x in location_data]
        self._group_labels = group_labels
        self._group_colors = None

    @property
    def group_labels(self):
        if self._group_labels is None:
            self._group_labels = ["Group {}".format(x) for x in range(len(
                self.group_colors))]
        return self._group_labels

    @property
    def group_colors(self):
        if self._group_colors is None:
            self._group_colors = []
            for m in self.items:
                if m.color not in self._group_colors:
                    self._group_colors.append(m.color)
        return self._group_colors

    def get_patches(self):
        patches = []
        for i in range(len(self.group_colors)):
            patches.append(Patch(
                facecolor=self.group_colors[i],
                label=self.group_labels[i]))

        empty = any(x.is_null for x in self.items)

        if empty:
            empty_opts = {**DEFAULT_MISSING}
            patches.append(Patch(**empty_opts))

        return patches


def data_converter(data):
    out = []
    for d in data:
        try:
            iter(d)
            group = []
            for k in d:
                group.append(ValueObject(k))
            out.append(GroupObject(group))
        except TypeError:
            out.append(ValueObject(d))

    return out


class AssembleBars:
    def __init__(self, data, pyplot):
        self.data = data
        self._plt = pyplot  # type : matplotlib.pylab
        self._color_list = None
        self._color_manager = None  # type: ColorManager
        self._axis = None
        self._show_missing = None
        self._legend_options = None
        self._show_legend = False
        self._orientation = "x"
        self._missing_options = None
        self._boundaries = False
        self._boundaries_options = None
        self._show_value = False
        self._value_options = None
        self._is_stacked = False
        self._tick_labels = None

    @property
    def missing_allowed(self):
        if self._show_missing is None:
            return False
        else:
            return self._show_missing

    @property
    def plt(self):
        return self._plt

    @property
    def orientation(self):
        return self._orientation

    def _prepare_colors(self):
        if self._color_manager is None:
            self._color_manager = ColorManager()

        if self._color_list is not None:
            self._color_manager.colors = self._color_list
        self._color_manager.update_colors(self.data)

    def _prepare_axis(self):
        self._axis = AxisObject(self.data,
                                is_stacked=self._is_stacked,
                                show_missing=self.missing_allowed,
                                labels=self._tick_labels)
        self._axis.calculate_ticks()

    def _prepare_legend(self):
        if not self._show_legend:
            return
        legend = LegendObject(self._axis.bars)
        opts = {
            "handles": legend.get_patches()
        }
        opts = {**opts, **self._legend_options}
        self.plt.legend(**opts)

    def _prepare_boundaries(self):
        if not self._boundaries:
            return

        opts = {
            "color": self._color_manager.boundary,
            "alpha": 0.5
        }
        opts = {**opts, **self._boundaries_options}

        obj = self.plt.axvspan
        if self.orientation == "y":
            obj = self.plt.axhspan

        for b in self._axis.boundaries:
            obj(b[0], b[1], **opts)

    def _prepare_values(self):
        if not self._show_value:
            return

        opts = {
            "ha": "center",
            "va": "center"
        }

        for b in self._axis.bars:

            # Do not annotate null values
            if b[1].is_null:
                continue

            loc = self._value_options["position"]
            if "secret" in self._value_options.keys() and self._is_stacked:
                loc = 0.5

            loc = loc * b[1].value + self._value_options["offset"] + b[2]
            val = b[1].value

            op = {**opts, **self._value_options}

            if loc < b[1].value and "color" not in op.keys():
                op["color"] = text_color(b[1].color)

            try:
                del op["position"]
                del op["offset"]
                del op["secret"]
            except KeyError:
                pass

            if self.orientation == "x":
                self.plt.text(b[0], loc, "{}".format(val), **op)
            else:
                self.plt.text(loc, b[0], "{}".format(val), **op)

    def barplot(self):
        main = self.plt.bar
        span = self.plt.axvspan
        ticks = self.plt.xticks
        if self.orientation == "y":
            main = self.plt.barh
            span = self.plt.axhspan
            ticks = self.plt.yticks

        for m in self._axis.bars:

            opts = {
                "color": m[1].color
            }

            if self.orientation == "y":
                opts["height"] = m[1].width
                opts["left"] = m[2]
            else:
                opts["width"] = m[1].width
                opts["bottom"] = m[2]

            if m[1].is_null:
                span(m[0] - m[1].width / 2, m[0] + m[1].width / 2,
                     **self._missing_options)
            else:
                main(m[0], m[1].value, **opts)

        ticks(self._axis.ticks, self._axis.labels)

    def draw(self):
        self._prepare_colors()
        self._prepare_axis()
        self._prepare_legend()
        self._prepare_boundaries()
        self._prepare_values()
        self.barplot()

    def show_missing(self, **kwargs):
        self._show_missing = True
        if self._missing_options is None:
            self._missing_options = {**DEFAULT_MISSING}
        self._missing_options = {**self._missing_options, **kwargs}

    def show_legend(self, **kwargs):
        self._show_legend = True
        if self._legend_options is None:
            self._legend_options = {}
        self._legend_options = {**self._legend_options, **kwargs}

    def swap_axis(self):
        if self._orientation == "x":
            self._orientation = "y"
        else:
            self._orientation = "x"

    def show_boundaries(self, **kwargs):
        self._boundaries = True
        if self._boundaries_options is None:
            self._boundaries_options = {}
        self._boundaries_options = {**self._boundaries_options, **kwargs}

    def colors(self, colors: list):
        if len(colors) == 0:
            return
        if type(colors) != list:
            colors = [colors]
        self._color_list = colors

    def group_gap(self, gap: float):
        for d in self.data:
            d.update_margin(gap)

    def sample_gap(self, gap: float):
        for d in self.data:
            d.gap = gap

    def width(self, value: float):
        for d in self.data:
            d.update_width(value)

    def show_values(self, position: float = None, offset: float = 0.01,
                    **kwargs):
        self._show_value = True
        self._value_options = {
            "position": position,
            "offset": offset}
        self._value_options = {**self._value_options, **kwargs}
        if position is None:
            self._value_options["position"] = 0.5
            self._value_options["secret"] = True

    def stack_bars(self):
        self._is_stacked = True

    def reversed(self):
        self.data = list(reversed(self.data))

    def add_tick_labels(self, labels: list):
        self._tick_labels = labels

    def show(self):
        self.draw()
        self.plt.tight_layout()
        self.plt.show()


def run():
    raw = [[50, 50, 20], [20, 30]]
    data = data_converter(raw)
    a = AssembleBars(data, plt)
    a.sample_gap(0.5)
    a.show_legend()
    a.add_tick_labels(["first", "second"])

    a.show()
