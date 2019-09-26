#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 23/09/19, 4:10 PM
#
#
#  All Matrix visualization objects

import matplotlib
from SecretColors import ColorMap

from SecretPlots.objects.base import Section, CategoryPlot
from SecretPlots.objects.shapes import *

p = Palette(show_warning=False)
ON_COLOR = p.peach(shade=30)
OFF_COLOR = p.ultramarine(shade=60)


class BooleanPlot:
    """
    BooleanPlot

    This is equivalent of heatmap but much more customizable and with lot of
    in-build options which user do not have to worry about. This plot
    essentially shows values in the BooleanForm. Where 1 will be shown in
    one color while 0 will be shown in another color. You can set threshold
    to your data and it will automatically format it.

    >>> data = [[12,44,120], [33,44,0], [224,2, 33]]
    >>> b = BooleanPlot(data)
    >>> b.threshold = 20
    >>> b.show()

    Default threshold if 1. So if your data is already in Boolean format
    then you don't have to set threshold separately. You can set threshold
    while construction of object as well

    >>> b = BooleanPlot(data, threshold=20)

    You can customize it as you wish

    >>> b = BooleanPlot(data)
    >>> b.width = 1.2 # Width of each item
    >>> b.height = 1 # Height of each item
    >>> b.x_gap = 0.5 # Gap between two columns
    >>> b.y_gap = 0.5 # Gap between two rows
    >>> b.x_lines = True # Draw vertical lines between items
    >>> b.y_lines = True # Draw horizontal lines between items
    >>> b.on_color = "g" # Set color of ON objects (one with value 1)
    >>> b.off_color = "k" # Set color of OFF objects (one with value 0)
    >>> b.y_labels = ["x", "y", "z"] # Labels for yticks
    >>> b.x_labels = ["g1", "g2", "g3"] # Labels for xticks
    >>> b.shape = "circle" # Change shape of boolean object to circle
    >>> b.add_legend() # Add legend
    >>> b.show()

    As this is completely based on matplotlib, you can essentially do any
    available customization on it.

    >>> fig, ax = plt.subplots()
    >>> b = BooleanPlot(data)
    >>> b.draw(ax) # Give your axes for drawing
    >>> ax.set_xlim(-1,10) # You can use your own customization
    >>> plt.show() # You need to manually use plt.show() at the end

    """

    def __init__(self, data, threshold=None):
        self._data = data
        self._threshold = threshold
        self._formatted_data = None
        self._width = None
        self._height = None
        self._y_gap = None
        self._x_gap = None
        self._y_lines = False
        self._x_lines = False
        self._x_labels = None
        self._y_labels = None
        self._x_ticks = None
        self._y_ticks = None
        self._x_labels_option = None
        self._y_labels_option = None
        self._x_lines_options = None
        self._y_lines_options = None
        self._shape = None
        self._options = {}
        self._legend = False
        self._legend_labels = None
        self._legend_options = None

        self.on_color = ON_COLOR
        self.off_color = OFF_COLOR

    @property
    def data(self):
        """
        Formatted data
        """
        if self._formatted_data is None:
            self._format_data()
        return self._formatted_data

    @property
    def rows(self):
        if len(self.data.shape) == 1:
            return len(self.data)
        elif len(self.data.shape) == 2:
            return self.data.shape[1]
        else:
            raise Exception("Currently this plot only accepts 2D data")

    @property
    def columns(self):
        if len(self.data.shape) == 1:
            return 1
        elif len(self.data.shape) == 2:
            return self.data.shape[0]
        else:
            raise Exception("Currently this plot only accepts 2D data")

    @property
    def width(self):
        """Width of the item"""
        if self._width is None:
            self._width = 1
        return self._width

    @width.setter
    def width(self, value):
        self._width = value

    @property
    def height(self):
        """Height of the items"""
        if self._height is None:
            self._height = 1
        return self._height

    @height.setter
    def height(self, value):
        self._height = value

    @property
    def threshold(self):
        """All values below threshold will be considered as 0 while all
        values equal to and greater than threshold will be considered as 1
        """
        if self._threshold is None:
            self._threshold = 1
        return self._threshold

    @threshold.setter
    def threshold(self, value):
        self._threshold = value

    @property
    def y_gap(self):
        """
        Gap between two rows
        """
        if self._y_gap is None:
            self._y_gap = 0
        return self._y_gap

    @y_gap.setter
    def y_gap(self, value):
        self._y_gap = value

    @property
    def x_gap(self):
        """
        Gap between two columns
        """
        if self._x_gap is None:
            self._x_gap = 0
        return self._x_gap

    @x_gap.setter
    def x_gap(self, value):
        self._x_gap = value

    @property
    def y_lines(self):
        """Lines between columns"""
        return self._y_lines

    @y_lines.setter
    def y_lines(self, value):
        self._y_lines = value

    @property
    def x_lines(self):
        """Lines between rows"""
        return self._x_lines

    @x_lines.setter
    def x_lines(self, value):
        self._x_lines = value

    @property
    def x_labels(self):
        """
        Xtick labels
        """
        if self._x_labels is None:
            if self.columns == 1:
                self._x_labels = ["0"]
            else:
                self._x_labels = ["{}".format(x) for x in range(self.columns)]

        return self._x_labels

    @x_labels.setter
    def x_labels(self, value):
        self._x_labels = value

    @property
    def y_labels(self):
        """
        Ytick labels
        """
        if self._y_labels is None:
            self._y_labels = ["Sample {}".format(x) for x in range(self.rows)]
        return self._y_labels

    @y_labels.setter
    def y_labels(self, value):
        self._y_labels = value

    @property
    def shape(self):
        """
        Shape of the Boolean items. Currently following shapes are available

        1) rectangle, rect, r
        2) triangle, tri, t
        3) circle, cir, c
        """
        if self._shape is None:
            self._shape = "rect"

        return self._shape

    @shape.setter
    def shape(self, value):
        self._shape = value

    @property
    def options(self):
        """
        These options will be passed in constructing Boolean objects. Use
        'add_options()' to add these options
        """
        return self._options

    @property
    def y_ticks(self):
        if self._y_ticks is None:
            t = []
            delay = 0
            for x in range(self.rows):
                delay += self.height / 2
                t.append(delay)
                delay += self.height / 2 + self.y_gap
            self._y_ticks = t
        return self._y_ticks

    @property
    def x_ticks(self):
        if self._x_ticks is None:
            t = []
            delay = 0
            for x in range(self.columns):
                delay += self.width / 2
                t.append(delay)
                delay += self.width / 2 + self.x_gap
            self._x_ticks = t

        return self._x_ticks

    @property
    def x_labels_option(self):
        """
        These options will be passed in generating xtick labels.
        """
        if self._x_labels_option is None:
            self._x_labels_option = {
                "rotation": 45,
                "ha": "left"}
        return self._x_labels_option

    @property
    def y_labels_option(self):
        """
        These options will be passed in generating ytick labels.
        """
        if self._y_labels_option is None:
            self._y_labels_option = {}
        return self._y_labels_option

    @property
    def x_lines_option(self):
        """
        These options will be passed in generating vertical lines. Use
        'add_xlines()' functions to add these options
        """
        if self._x_lines_options is None:
            self._x_lines_options = {
                "color": p.black()
            }
        return self._x_lines_options

    @property
    def y_lines_option(self):
        """
        These options will be passed in generating horizontal lines. Use
        'add_ylines()' functions to add these options
        """
        if self._y_lines_options is None:
            self._y_lines_options = {
                "color": p.black()
            }
        return self._y_lines_options

    @property
    def legend_options(self):
        """
        Options which will be passed while generating legends
        """
        if self._legend_options is None:
            self._legend_options = {
                "bbox_to_anchor": (1, 1)
            }
        return self._legend_options

    @property
    def legend_labels(self):
        """
        Labels of the legends. This value will be override if you have used
        'label' property in the 'add_legend()' function
        """
        if self._legend_labels is None:
            self._legend_labels = ["ON", "OFF"]
        return self._legend_labels

    @legend_labels.setter
    def legend_labels(self, values):
        self._legend_labels = values

    def _format_data(self):
        data = self._data
        data = np.asarray(data)
        data[data < self.threshold] = 0
        data[data >= self.threshold] = 1
        self._formatted_data = data

    def _get_shape_class(self):
        if self.shape.lower().strip() in ["rect", "rectangle", "r"]:
            return Rectangle
        elif self.shape.lower().strip() in ["tri", "triangle", "t"]:
            return Triangle
        elif self.shape.lower().strip() in ["cir", "circle", "c"]:
            return Circle
        else:
            raise Exception("Shape {} is not available in BooleanPlot "
                            "yet".format(self.shape))

    def _get_columns(self, rows, x_loc):
        items = []
        for i, x in enumerate(rows):
            y = i * (self.height + self.y_gap)

            opts = {"color": self.on_color}
            if x == 0:
                opts["color"] = self.off_color

            opts = {**opts, **self.options}
            obj = self._get_shape_class()(x_loc, y, self.width, self.height,
                                          **opts)
            items.append(obj.get())
        return items

    def _draw_items(self, ax):
        items = []
        if self.columns == 1:
            items.extend(self._get_columns(self.data, 0))

        else:
            for i, col in enumerate(self.data):
                items.extend(
                    self._get_columns(col, i * (self.width + self.x_gap)))

        for item in items:
            ax.add_patch(item)

    def _draw_axis(self, ax):
        ax.set_xlim((0, self.columns * (self.width + self.x_gap)))
        ax.set_ylim((0, self.rows * (self.height + self.y_gap)))
        ax.set_aspect("equal")
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.xaxis.tick_top()
        ax.yaxis.set_ticks(self.y_ticks)
        ax.xaxis.set_ticks(self.x_ticks)
        ax.yaxis.set_ticklabels(self.y_labels, **self.y_labels_option)
        ax.xaxis.set_ticklabels(self.x_labels, **self.x_labels_option)

    def _draw_lines(self, ax):
        if self.x_lines:
            for i, x in enumerate(self.x_ticks[:-1]):
                temp = (x + self.x_ticks[i + 1]) / 2
                ax.axvline(temp, **self.x_lines_option)

        if self.y_lines:
            for i, y in enumerate(self.y_ticks[:-1]):
                temp = (y + self.y_ticks[i + 1]) / 2
                ax.axhline(temp, **self.y_lines_option)

    def _draw_legend(self, ax):
        if not self._legend:
            return

        opts = {
            "handles": self.get_legend_patches()
        }

        opts = {**opts, **self.legend_options}
        ax.legend(**opts)

    def get_legend_patches(self):
        """
        :return: Patches used for generating legends
        """
        return [
            patches.Patch(facecolor=self.on_color, label="ON"),
            patches.Patch(facecolor=self.off_color, label="OFF")
        ]

    def draw(self, ax=None):
        """
        Draws the plot on the given axes

        :param ax: Matplotlib axes or plt.gca() (if not given)

        After drawing, you can have your own customization. However ,
        you need to invoke plt.show() or plt.savefig() manually to see your
        plot with all the customizations

        >>> b = BooleanPlot(data)
        >>> b.draw()
        >>> plt.yticks([])
        >>> plt.show()
        """
        if ax is None:
            ax = plt.gca()

        self._draw_items(ax)
        self._draw_axis(ax)
        self._draw_lines(ax)
        self._draw_legend(ax)

    def add_xlines(self, **kwargs):
        """
        Vertical Lines in between xticks
        :param kwargs: Standard matplotlib artists

        >>> b.add_xlines(linestyle="--", color="r")
        """
        self._x_lines = True
        self._x_lines_options = {**self.x_lines_option, **kwargs}

    def add_ylines(self, **kwargs):
        """
        Horizontal Lines in betweeb yticks
        :param kwargs: Standard matplotlib artists

        >>> b.add_ylines(linestyle="--", color="r")
        """
        self._y_lines = True
        self._y_lines_options = {**self.y_lines_option, **kwargs}

    def add_lines(self, **kwargs):
        """
        Adds both vertical and horizontal lines between ticks
        :param kwargs: Standard matplotlib artists

        >>> b.add_lines(linestyle="--", color="b")
        """
        self.add_xlines(**kwargs)
        self.add_ylines(**kwargs)

    def add_legend(self, **kwargs):
        """
        Adds legend to the plot
        :param kwargs: Standard matplotlib legends

        >>> b.add_legend(labels=["x", "y", "z"], loc=0)
        """
        self._legend = True
        self._legend_options = {**self.legend_options, **kwargs}

    def add_options(self, **kwargs):
        """
        Patch options. These options will be passed to the shapes which are
        used in generating Boolean Values
        :param kwargs: Standard matplotlib patch artists

        >>> b.add_options(fill=False, hatch="//")

        """
        self._options = {**self.options, **kwargs}

    def show(self, ax=None, tight: bool = True):
        """
        Shows the plot

        :param ax: Matplotlib axes (if not provided, standard axes will be
        derived from plt.gca())
        :param tight: If True, tight layout will be used

        >>> b = BooleanPlot(data)
        >>> b.show()

        If you want more customization, you can use `draw` and add your own
        customization
        """
        self.draw(ax)
        if tight:
            plt.tight_layout()
        plt.show()

    def save(self, filename, ax=None, tight=True, **kwargs):
        """
        Saves the plot
        :param filename: Name of the file
        :param ax: matplotlib axes or plt.gca() (if not given)
        :param tight: if True, tightlayout will be used
        :param kwargs: Any options which accepted by plt.savefig() function
        """

        self.draw(ax)
        if tight:
            plt.tight_layout()
        plt.savefig(filename, **kwargs)


class HeatPlot(CategoryPlot):

    def __init__(self, data):
        super().__init__()
        self._raw_data = data
        self._additional_data = []
        self._section_gap = None
        self._width = None
        self._height = None
        self._major_pos = None
        self._minor_pos = None
        self._positions = None
        self.rotations = 0
        self._cmap = None
        self._colorbar = False

    @property
    def positions(self):
        if self._positions is None:
            self._positions = []
            x = self.major_pos
            y = self.minor_pos
            if self.orientation == "y":
                x, y = y, x

            x_count = 0
            y_count = 0

            def _update(xx, yy):
                if self.orientation == "x":
                    return xx + 1, 0
                else:
                    return 0, yy + 1

            def _minor(xx, yy):
                if self.orientation == "x":
                    return xx, yy + 1
                else:
                    return xx + 1, yy

            for s in self.sections:
                for d in s.data:
                    if d.is_single_valued:
                        self._positions.append((x[x_count], y[y_count]))
                        x_count, y_count = _update(x_count, y_count)
                    else:
                        if d.columns == 1:
                            for m in d.value:
                                self._positions.append((x[x_count],
                                                        y[y_count]))
                                x_count, y_count = _minor(x_count, y_count)
                            x_count, y_count = _update(x_count, y_count)
                        else:
                            for m in d.value:
                                for k in m:
                                    self._positions.append(
                                        (x[x_count], y[y_count]))
                                    x_count, y_count = _minor(x_count, y_count)
                                x_count, y_count = _update(x_count, y_count)

        return self._positions

    @property
    def width(self):
        if self._width is None:
            self._width = 1
        return self._width

    @width.setter
    def width(self, value: float):
        self._width = value

    @property
    def height(self):
        if self._height is None:
            self._height = 1
        return self._height

    @height.setter
    def height(self, value):
        self._height = value

    @property
    def cmap(self):
        if self._cmap is None:
            c = ColorMap(matplotlib, p).greens()
            self._cmap = c
        return self._cmap

    @property
    def section_gap(self):
        if self._section_gap is None:
            self._section_gap = 1
        return self._section_gap

    @property
    def major_pos(self):
        if self._major_pos is None:
            self._set_positions()
        return self._major_pos

    @property
    def minor_pos(self):
        if self._minor_pos is None:
            self._set_positions()
        return self._minor_pos

    @property
    def sections(self):
        if len(self._sections) == 0:
            s = Section(margin=self.section_gap)
            s.add_data(self._raw_data)
            self._sections.append(s)
            for d in self._additional_data:
                s2 = Section(margin=self.section_gap)
                s2.add_data(d)
                self._sections.append(s2)
        return self._sections

    def _calculate_pos(self, gap, value, is_column):
        current_pos = None
        major_pos = []
        for s in self.sections:
            if not is_column:
                current_pos = None
            for d in s.data:
                if current_pos is None:
                    current_pos = 0
                else:
                    current_pos += gap + value
                if d.is_single_valued:
                    major_pos.append(current_pos)
                    current_pos += self.section_gap
                else:
                    no = d.rows
                    if is_column:
                        no = d.columns
                    for k in range(no):
                        if current_pos not in major_pos:
                            major_pos.append(current_pos)
                        current_pos += gap + value

            current_pos += self.section_gap - gap - value

        return major_pos

    def _set_positions(self):
        if self.orientation == "x":
            major_pos = self._calculate_pos(self.x_gap, self.width, True)
            minor_pos = self._calculate_pos(self.y_gap, self.height, False)
        else:
            major_pos = self._calculate_pos(self.y_gap, self.height, True)
            minor_pos = self._calculate_pos(self.x_gap, self.width, False)

        self._major_pos = major_pos
        self._minor_pos = minor_pos

    @property
    def shape(self):
        return Rectangle

    def get_color(self, value):
        try:
            m = max([x.max for x in self.sections])
            n = min([x.min for x in self.sections])
            norm = matplotlib.colors.Normalize(vmin=n, vmax=m)
            return self.cmap(norm(value))
        except TypeError:
            return p.red(shade=40)

    def _draw_axis(self, ax):
        x_pos = [x[0] for x in self.positions]
        y_pos = [x[1] for x in self.positions]

        ax.set_xlim(min(x_pos) - self.x_padding[0],
                    max(x_pos) + self.width + self.x_padding[1])
        ax.set_ylim(min(y_pos) - self.y_padding[1],
                    max(y_pos) + self.height + self.y_padding[0])
        # ax.set_aspect("equal")

        ticks = list(set([x + self.width / 2 for x in self.major_pos]))
        ticks_other = list(set([x + self.height / 2 for x in self.minor_pos]))
        major_label = ["S{}".format(x) for x in range(len(ticks))]
        minor_label = ["{}".format(x) for x in range(len(ticks_other))]

        self.check_labels(major_label, minor_label)

        if self.orientation == "y":
            ticks, ticks_other = ticks_other, ticks
            major_label, minor_label = minor_label, major_label

        ax.set_xticks(ticks)
        ax.set_xticklabels(self.x_labels, **self.x_label_options)
        ax.set_yticks(ticks_other)
        ax.set_yticklabels(self.y_labels, **self.y_label_options)

    def _draw_colorbar(self, ax):

        if not self._colorbar:
            return

        m = max([x.max for x in self.sections])
        n = min([x.min for x in self.sections])
        norm = matplotlib.colors.Normalize(vmin=n, vmax=m)
        sm = plt.cm.ScalarMappable(cmap=self.cmap, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ax=ax)

    def _draw_sections(self, ax):

        def __add(i, options):
            ax.add_patch(
                self.shape(
                    self.positions[i][0],
                    self.positions[i][1],
                    self.width,
                    self.height,
                    self.rotations,
                    **options
                ).get()
            )

        def __options(value):
            return {"color": self.get_color(value)}

        count = 0
        for s in self.sections:
            for d in s.data:
                if d.is_single_valued:
                    __add(count, __options(d.value))
                    count += 1
                else:
                    for c in d.value:
                        try:
                            for v in c:
                                __add(count, __options(v))
                                count += 1
                        except TypeError:
                            __add(count, __options(c))
                            count += 1

    def add_data(self, data):
        self._additional_data.append(data)

    def add_cmap(self, name):
        self._cmap = matplotlib.cm.get_cmap(name)

    def draw(self, ax):
        self._draw_sections(ax)
        self._draw_axis(ax)
        self._draw_colorbar(ax)
        plt.show()


def run():
    data = [np.random.uniform(-100, 100, 5) for x in range(3)]
    h = HeatPlot(data)
    fig, ax = plt.subplots()
    h.draw(ax)
