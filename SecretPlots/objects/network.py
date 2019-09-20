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
    _COUNT = 0

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


def draw_text_at_center(ax, rect: Rectangle, text: str):
    x = rect.x + rect.width / 2
    y = rect.y + rect.height / 2
    ax.text(x, y, text, ha="center", va="center",
            color="w", fontsize=12)


class Node:
    def __init__(self, name):
        self.name = name
        self._origins = []
        self._destinations = []
        self._location = None
        self._color = None
        self.width = None
        self.height = None
        self._rectangle = None

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    @property
    def origins(self):
        return self._origins

    @property
    def destinations(self):
        return self._destinations

    def add_interactions(self, val: Interaction):
        if val.origin == self.name:
            val.number = len(self._origins)
            self._origins.append(val)

        if val.target == self.name:
            val.number = len(self._destinations)
            self._destinations.append(val)

    def get_origin_points(self):
        points = []

        x1, y = self.location
        x2 = x1 + self.width

        for x in np.linspace(x1, x2, len(self.origins) + 2):
            points.append((x, y))

        return points[1:-1]

    def get_destination_points(self):
        points = []
        x1, y = self.location
        y += self.height
        x2 = x1 + self.width

        for x in np.linspace(x1, x2, len(self.destinations) + 2):
            points.append((x, y))

        return points[1:-1]

    @property
    def rectangle(self):
        if self._rectangle is None:
            self._rectangle = Rectangle(
                self.location[0],
                self.location[1],
                self.width,
                self.height,
                color=self.color
            )
        return self._rectangle


def intermediates(point1, point2, start_no, dest_no,
                  node1, node2, stem, extra_x, extra_y):
    def __add_x(m):
        k = m
        while k in extra_x:
            k -= stem
        return k

    def __add_y(m):
        if m in extra_y:
            return m + stem
        return m

    x1, y1 = point1
    x2, y2 = point2
    x3, y3 = node1.location
    x4, y4 = node2.location

    # First Point and Stem
    p = [point1, (x1, y1 - stem * (start_no + 1))]
    p.append((__add_x(x3 - stem * (start_no + 1)), p[-1][1]))
    p.append((p[-1][0], __add_y(y2 + stem * (dest_no + 1))))
    p.append((x2, p[-1][1]))

    return p


class Network:
    def __init__(self, interactions: list):
        self.interactions = sorted(interactions, key=lambda x: x.flat)
        self._nodes = None
        self._columns = 2
        self._locations = None
        self._width = 0.4
        self._height = 0.3
        self.palette = Palette()
        self._colors = None
        self._vertical_gap = 1.5
        self._horizontal_gap = 0.8
        self._node_objects = None
        self._node_dict = None
        self._node_stem = 0.1
        self._extra_x = []
        self._extra_y = []

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def columns(self):
        return self._columns

    @property
    def nodes(self):
        if self._nodes is None:
            n = []
            for k in self.interactions:
                n.extend(k.nodes)
            self._nodes = sorted(list(set(n)))
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
                    h_gap += self._horizontal_gap
                h_gap = 0
                v_gap += self._vertical_gap

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

    def _color_cycle(self):
        while True:
            for x in self.palette.get_color_list:
                yield x

    @property
    def colors(self):
        if self._colors is None:
            cycle = self._color_cycle()
            self._colors = []
            for i in self.nodes:
                self._colors.append(next(cycle))
        return self._colors

    def _draw_text(self, ax):
        for m in self.node_objects:
            ax.add_patch(m.rectangle.get())
            draw_text_at_center(ax, m.rectangle, m.name)

    def _connect_nodes(self, start: Node, end: Node, count):
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
        points = intermediates((x1, y1), (x2, y2),
                               start_no, dest_no,
                               start, end,
                               self._node_stem,
                               self._extra_x, self._extra_y)

        self._extra_x.extend([x[0] for x in points])
        self._extra_y.extend([y[1] for y in points])

        return Line2D([x[0] for x in points], [x[1] for x in points],
                      color=start.color)

    def _draw_lines(self, ax):
        for i in self.interactions:

            origin = self.node_dict[i.origin]
            target = self.node_dict[i.target]

            p = self._connect_nodes(self.node_dict[i.origin],
                                    self.node_dict[i.target], i.count)

            ax.annotate(
                "", (
                    p.get_xdata()[-1],
                    self.node_dict[i.target].location[1]),
                xytext=(p.get_xdata()[-1],
                        p.get_ydata()[-1] + self._node_stem),
                arrowprops=dict(arrowstyle='->',
                                color=self.node_dict[i.origin].color)
            )

            ax.add_line(p)

    def draw(self, ax):
        self._draw_text(ax)
        self._draw_lines(ax)


def run():
    data = [Interaction(["a", "c", 1]),
            Interaction(["c", "b", 1]),
            Interaction(["k", "b2", 1]),
            Interaction(["a", "b", 1]),
            Interaction(["k", "b", 1]),
            Interaction(["c", "d2", 1])]

    n = Network(data)

    fig, ax = plt.subplots()

    n.draw(ax)
    ax.set_xlim(-1, 3)
    ax.set_ylim(-1, 4)
    ax.set_axis_off()
    plt.show()
