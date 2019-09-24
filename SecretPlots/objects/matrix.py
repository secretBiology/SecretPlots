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

from SecretPlots.objects.shapes import *

p = Palette()
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


def run():
    data = [np.random.uniform(-100, 100, 10) for x in range(6)]
    m = BooleanPlot(data)
    m.show()
