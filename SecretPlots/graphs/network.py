#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 20/09/19, 9:33 AM
#
#
#  Objects related to the Network plotting

import matplotlib.pyplot as plt
import numpy as np
from SecretColors import Palette
from matplotlib.lines import Line2D

from SecretPlots.objects.shapes import Rectangle


class Interaction:
    """
    Simple class to hold the interaction data

    Feed data in the form of list
    data = [origin_node:str, target_node:str, type_of_interaction:int]

    Type of interaction can be
    1 : Positive Interaction
    0 : Negative Interaction
    -1: No arrow, just connection
    """

    _COUNT = 0  # Need this in case of duplicate interactions

    def __init__(self, data):
        self.count = Interaction._COUNT
        Interaction._COUNT += 1
        self.data = data
        self.origin = data[0]
        self.target = data[1]
        self.type = data[2]
        self.number = 0
        self.flat = "{}{}{}".format(self.origin, self.target, self.type)

    @property
    def nodes(self):
        if self.origin == self.target:
            return [self.origin]
        else:
            return [self.origin, self.target]


def draw_text_at_center(ax, rect: Rectangle, text: str, options: dict) -> None:
    """Draws text at the center of rectangle

    :param ax: Matplotlib Axes
    :param rect: Rectangle (:class:`SecretPlots.objects.shapes.Rectangle`)
    :param text: Text to be added (string)
    :param options: Text formatting options (dictionary)
    :return: None

    """

    x = rect.x + rect.width / 2
    y = rect.y + rect.height / 2

    # Default options
    opts = {"ha": "center",
            "va": "center",
            "color": "w",
            "fontsize": 12}

    opts = {**opts, **options}

    ax.text(x, y, text, **opts)


class Node:
    """
    Class to hold all the properties of the nodes in the
    '~SecretPlots.objects.network.NetworkPlot'
    """

    def __init__(self, name):
        self.name = name
        self._origins = []
        self._destinations = []
        self._location = None
        self._color = None
        self.width = None
        self.height = None
        self._rectangle = None
        self.options = None

    @property
    def location(self):
        """
        Lower left point of the node
        :return: (x, y)
        """
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    @property
    def color(self):
        """
        Color of the node
        :return: String or Tuple
        """
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    @property
    def origins(self):
        """
        Other node connections which will be originated from this Node
        :return: List of Nodes
        """
        return self._origins

    @property
    def destinations(self):
        """
        Other node connections which will target this Node
        :return: List of nodes
        """
        return self._destinations

    def add_interactions(self, val: Interaction):
        """
        Adds interaction to the Node
        :param val: :class:`~SecretPlots.objects.network.Interaction`
        """
        if val.origin == self.name:
            val.number = len(self._origins)
            self._origins.append(val)

        if val.target == self.name:
            val.number = len(self._destinations)
            self._destinations.append(val)

    def get_origin_points(self):
        """
        (x,y) location of all origin nodes available
        :return: List of coordinates
        """
        points = []

        x1, y = self.location
        x2 = x1 + self.width

        for x in np.linspace(x1, x2, len(self.origins) + 2):
            points.append((x, y))

        return points[1:-1]

    def get_destination_points(self):
        """
        (x,y) location of all destination nodes available
        :return: List of coordinates
        """
        points = []
        x1, y = self.location
        y += self.height
        x2 = x1 + self.width

        for x in np.linspace(x1, x2, len(self.destinations) + 2):
            points.append((x, y))

        return points[1:-1]

    @property
    def rectangle(self):
        """Makes rectangle which will be used as node
        :return: :class:`~SecretPlots.objects.shapes.Rectangle`
        """
        if self._rectangle is None:
            opts = {"color": self.color}

            if self.options is not None:
                opts = {**opts, **self.options}

            self._rectangle = Rectangle(
                self.location[0],
                self.location[1],
                self.width,
                self.height,
                **opts
            )
        return self._rectangle


def _intermediates(point1, point2, start_no, dest_no,
                   node1, node2, stem, extra_x, extra_y,
                   arrow_type):
    """
    Finds the intermediate points between two nodes

    :param point1: Origin point (tuple)
    :param point2: Destination Point (tuple)
    :param start_no: Index on origin node
    :param dest_no: Index on destination node
    :param node1: Origin Node
    :param node2: Destination Node
    :param stem: Size of initial line outgrowth
    :param extra_x: all the previous x coordinates
    :param extra_y: all the previoys y coordinates
    :param arrow_type: Type of arrow
    :return: list of matplotlib.patches.Line2D
    """

    def __add_x(m):
        k = m
        while k in extra_x:
            k -= stem / 2
        return k

    def __add_y(m):
        k = m
        while k in extra_y:
            k += stem / 2
        return k

    x1, y1 = point1
    x2, y2 = point2
    x3, y3 = node1.location
    x4, y4 = node2.location

    # First Point and Stem
    p = [point1, (x1, y1 - stem * (start_no + 1))]
    p.append((__add_x(x3 - stem * (start_no + 1)), p[-1][1]))
    p.append((p[-1][0], __add_y(y2 + stem * (dest_no + 1))))
    p.append((x2, p[-1][1]))
    p.append(point2)

    if arrow_type == -1:
        return p

    arrow_width = 0.02
    arrow_height = 0.05
    # Add Arrow Head
    if arrow_type == 1:
        p.append((p[-1][0] + arrow_width, p[-1][1] + arrow_height))
        p.append(point2)
        p.append((p[-1][0] - arrow_width, p[-1][1] + arrow_height))
    elif arrow_type == 0:
        p.pop(-1)
        p.append((p[-1][0], y2 + stem * 0.25))
        p.append((p[-1][0] + arrow_width, p[-1][1]))
        p.append((p[-1][0] - 2 * arrow_width, p[-1][1]))

    return p


class Network:
    """
    Main class of the NetworkPlot

    You can set following properties of the network

    columns: number of columns in which network will be arranged
    width: Width of the node rectangles
    height: Height of the node rectangles
    colors: Colors to assign to nodes. If there are less number of colors
    than the available nodes, colors will be repeated again from the start
    vertical_gap: Space between two rows
    horizontal_gap: Space between two columns
    node_stem: Initial size of the connection line
    node_options: options which can be set to the node rectangles. These
    includes all the options which we can set to matplotlib.patches
    text_options: options which can be set to the text shown on the nodes.
    These includes all the standard text formatting options
    line_options: options which can be set to the connection lines. All
    standard Line2D options will work
    """

    def __init__(self, interactions: list, node_preference=None):
        self.interactions = sorted(interactions, key=lambda x: x.flat)
        self._nodes = None
        self._columns = 2
        self._locations = None
        self._width = 0.5
        self._height = 0.4
        self.palette = Palette()
        self._colors = None
        self._vertical_gap = None
        self._horizontal_gap = None
        self._node_objects = None
        self._node_dict = None
        self._node_stem = None
        self._extra_x = []
        self._extra_y = []
        self.node_preference = node_preference
        self._node_options = None
        self._text_options = None
        self._line_options = None

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        self._columns = value

    @property
    def vertical_gap(self):
        if self._vertical_gap is None:
            self._vertical_gap = max(self.height * 1.5, 1)

        return self._vertical_gap

    @vertical_gap.setter
    def vertical_gap(self, value):
        self._vertical_gap = value

    @property
    def horizontal_gap(self):
        if self._horizontal_gap is None:
            self._horizontal_gap = max(self.width * 1.5, 1)

        return self._horizontal_gap

    @horizontal_gap.setter
    def horizontal_gap(self, value):
        self._horizontal_gap = value

    @property
    def node_stem(self):
        if self._node_stem is None:
            return max(self.height * 0.2, 0.15)
        return self._node_stem

    @property
    def nodes(self):
        if self._nodes is None:
            n = []
            for k in self.interactions:
                n.extend(k.nodes)
            if self.node_preference is None:
                self._nodes = sorted(list(set(n)))
            else:
                n = list(set(n))
                self._nodes = []
                for p in self.node_preference:
                    if p in n:
                        self._nodes.append(p)
                        n.remove(p)
                self._nodes.extend(n)
        return self._nodes

    @property
    def locations(self):
        if self._locations is None:
            self._locations = []
            chunks = [self.nodes[i:i + self.columns]
                      for i in range(0, len(self.nodes), self.columns)]
            v_gap = 0
            h_gap = 0
            for i in range(len(chunks)):
                for j in chunks[i]:
                    self._locations.append((h_gap, v_gap))
                    h_gap += self.horizontal_gap
                h_gap = 0
                v_gap += self.vertical_gap

        return self._locations

    @property
    def node_objects(self):
        if self._node_objects is None:
            self._node_objects = []
            for i, n in enumerate(self.nodes):
                obj = Node(n)
                obj.location = self.locations[i]
                obj.color = self.colors[i]
                obj.width = self.width
                obj.height = self.height
                obj.options = self._node_options
                for m in self.interactions:
                    obj.add_interactions(m)
                self._node_objects.append(obj)

        return self._node_objects

    @property
    def node_dict(self):
        if self._node_dict is None:
            self._node_dict = {}
            for n in self.node_objects:
                self._node_dict[n.name] = n

        return self._node_dict

    @staticmethod
    def _color_cycle(colors):
        while True:
            for x in colors:
                yield x

    @property
    def colors(self):
        if self._colors is None:
            cycle = self._color_cycle(self.palette.get_color_list)
            self._colors = []
            for i in self.nodes:
                self._colors.append(next(cycle))
        return self._colors

    @colors.setter
    def colors(self, color_list: list):
        if type(color_list) == str:
            color_list = [color_list]
        cycle = self._color_cycle(color_list)
        self._colors = []
        for i in self.nodes:
            self._colors.append(next(cycle))

    def _draw_text(self, ax):
        for m in self.node_objects:
            ax.add_patch(m.rectangle.get())
            opts = {}
            if self._text_options is not None:
                opts = {**opts, **self._text_options}
            draw_text_at_center(ax, m.rectangle, m.name, opts)

    def _connect_nodes(self, start: Node, end: Node, count, int_type):
        start_no = 0
        for i, s in enumerate(start.origins):
            if s.count == count:
                start_no = i

        x1, y1 = start.get_origin_points()[start_no]

        dest_no = 0
        for i, s in enumerate(end.destinations):
            if s.count == count:
                dest_no = i

        x2, y2 = end.get_destination_points()[dest_no]
        points = _intermediates((x1, y1), (x2, y2),
                                start_no, dest_no,
                                start, end,
                                self.node_stem,
                                self._extra_x, self._extra_y, int_type)

        self._extra_x.extend([x[0] for x in points])
        self._extra_y.extend([y[1] for y in points])

        opts = {"color": start.color}
        if self._line_options is not None:
            opts = {**opts, **self._line_options}

        return Line2D([x[0] for x in points], [x[1] for x in points], **opts)

    def _draw_lines(self, ax):
        for i in self.interactions:
            origin = self.node_dict[i.origin]
            target = self.node_dict[i.target]
            p = self._connect_nodes(origin, target, i.count, i.type)
            ax.add_line(p)

    def draw(self, ax):
        self._draw_text(ax)
        self._draw_lines(ax)

    def options(self, **kwargs):
        self._node_options = kwargs

    def text_options(self, **kwargs):
        self._text_options = kwargs

    def line_options(self, **kwargs):
        self._line_options = kwargs


class NetworkPlot:
    """
    NetworkPlot class

    This object can be used to generate the network plot which includes
    nodes and their connections

    >>> data = [["a","b", 1], ["b", "a", 1]]
    >>> n = NetworkPlot(data)
    >>> n.show()

    you can access the network object from the NetworkPlot which can be used
    for further customizations

    >>> network = n.network
    >>> network.width = 1
    >>> network.height = 0.7

    You can directly save the plot instead showing
    >>> n.save("filename.png")

    Save command includes all the options of matplotlib.pyplot.show() command
    >>> n.save("filename.png", dpi=300, format="png")

    """

    def __init__(self, data):
        self._data = data
        self._interactions = None
        self._network = None
        self._fig_drawn = False

    @property
    def interactions(self):
        if self._interactions is None:
            self._interactions = []
            for d in self._data:
                self._interactions.append(Interaction(d))

        return self._interactions

    @property
    def network(self):
        """
        :return: '~SecretPlots.objects.network.Network'
        """
        if self._network is None:
            self._network = Network(self.interactions)
        return self._network

    def _draw(self, ax):
        self.network.draw(ax)
        ax.set_axis_off()
        self._set_limit(ax)

    def _set_limit(self, ax):
        all_x = []
        all_y = []
        for n in self.network.node_objects:
            all_x.append(n.location[0])
            all_y.append(n.location[1])
            all_x.append(n.location[0] + n.width)
            all_y.append(n.location[1] + n.height)

        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y)
        max_y = max(all_y)

        ax.set_xlim(min_x - 1, max_x + 1)
        ax.set_ylim(min_y - 1, max_y + 1)

    def options(self, **kwargs):
        """
        Options which will be passed to the Rectangle drawn as a node
        These are global options and will be applied to all the nodes

        >>> n.options(hatch="//", fill=False)
        """
        self.network.options(**kwargs)

    def text_options(self, **kwargs):
        """
        Options which will be passed to the text drawn on each node
        These are global options and will be applied to all text

        >>> n.text_options(color="k", fontsize=10)
        """
        self.network.text_options(**kwargs)

    def line_options(self, **kwargs):
        """
        Options which will be passed to the connection lines
        These are global options and will be applied to all connection lines

        >>> n.midline_options(linestyle="--")
        """
        self.network.line_options(**kwargs)

    def show(self, ax=None):
        """
        Shows the NetworkPlot
        :param ax: matplotlib.axes (if not provided, default axes will be
        extracted from 'plt.gca()')

        >>> n.show()
        >>> fig, ax = plt.subplots()
        >>> n.show(ax)
        """
        if ax is None:
            ax = plt.gca()

        if not self._fig_drawn:
            self._draw(ax)
            self._fig_drawn = True
        plt.show()

    def save(self, filename: str, ax=None, **kwargs):
        """
        Saves the network plot
        :param filename: Name of the file
        :param ax: matplotlib.axes (if not provided, default axes will be
        extracted  from 'plt.gca()')
        :param kwargs: Any value which can be passed through plt.savefig()

        >>> n.save("filename.png", dpi = 300)
        """
        if ax is None:
            ax = plt.gca()

        if not self._fig_drawn:
            self._draw(ax)
            self._fig_drawn = True

        plt.savefig(filename, **kwargs)


def plot_network(data):
    """
    Simple function which shows the network plot.
    Use :class:`~SecretPlots.objects.network.NetworkPlot` for better
    customization

    :param data: List of interactions

    >>> data = [["a", "b", 1], ["b", "c", 1]]
    >>> plot_network(data)

    For better customization, use following
    >>> n = NetworkPlot(data)
    >>> n.show()

    """
    n = NetworkPlot(data)
    n.show()
    return n


def run():
    data = [["nkx2.5", "gata5", 1],
            ["nkx2.5", "tbx5a", 1],
            ["tbx5a", "tbx5a", 1],
            ["gata4", "hand2", 1]]

    fig, ax = plt.subplots()
    n = NetworkPlot(data)
    n.show()
