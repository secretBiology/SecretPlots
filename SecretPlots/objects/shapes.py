#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 19/09/19, 10:41 AM
#
#
# All Shapes will be accessed from this script


import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from SecretColors import Palette
from matplotlib.path import Path

palette = Palette()


class Rectangle:
    def __init__(self, x, y, width, height,
                 rotation: float = 0.0,
                 align: str = "center",
                 **kwargs):
        self._x = x
        self._y = y
        self._height = height
        self._width = width
        self._rotation = rotation
        self._align = align
        self._options = kwargs

    @property
    def align(self):
        return self._align

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def height(self):
        return self._height

    @property
    def width(self):
        return self._width

    @property
    def rotation(self):
        return self._rotation

    @property
    def options(self):
        if "color" not in self._options.keys():
            self._options["color"] = palette.blue()
        return self._options

    def get(self):
        return patches.Rectangle((self.x, self.y),
                                 self.width,
                                 self.height,
                                 self.rotation, **self.options)

    @property
    def color(self):
        return self.options["color"]


class Cuts:
    def __init__(self, obj,
                 no_of_cuts: int = 3,
                 cut_direction: str = None,
                 cut_depth: float = 1,
                 position: str = "top",
                 **kwargs):
        self._object = obj
        self.no_of_cuts = no_of_cuts
        self._cut_direction = cut_direction
        self.cut_depth = cut_depth
        self.position = position
        self._options = kwargs

    @property
    def object(self):
        return self._object

    @property
    def options(self):
        return self._options

    @staticmethod
    def _real_quadrant(angle):
        return abs(angle % 360)

    @property
    def cut_direction(self):
        if self._cut_direction is None:
            if self.position == "top":
                if 0 < self._real_quadrant(self.object.rotation) <= 180:
                    self._cut_direction = "in"
                else:
                    self._cut_direction = "out"
            elif self.position == "right":
                if 0 <= self._real_quadrant(self.object.rotation) < 180:
                    self._cut_direction = "out"
                else:
                    self._cut_direction = "in"
            elif self.position == "bottom":
                if 0 < self._real_quadrant(self.object.rotation) <= 180:
                    self._cut_direction = "out"
                else:
                    self._cut_direction = "in"
            elif self.position == "left":
                if 0 <= self._real_quadrant(self.object.rotation) < 180:
                    self._cut_direction = "in"
                else:
                    self._cut_direction = "out"
            else:
                raise Exception("Unknown cut position {}".format(
                    self.position))
        return self._cut_direction

    @property
    def start(self):
        if self.position in ["bottom", "left"]:
            return self.object.get().get_verts()[0]
        elif self.position == "right":
            return self.object.get().get_verts()[1]
        elif self.position == "top":
            return self.object.get().get_verts()[3]
        else:
            raise Exception("Unknown cut position {}".format(self.position))

    @property
    def end(self):
        if self.position == "bottom":
            return self.object.get().get_verts()[1]
        elif self.position == "left":
            return self.object.get().get_verts()[3]
        elif self.position in ["top", "right"]:
            return self.object.get().get_verts()[2]
        else:
            raise Exception("Unknown cut position {}".format(self.position))

    @staticmethod
    def simple_connect(vert: list):
        code = [Path.MOVETO]
        code.extend([Path.LINETO] * (len(vert) - 2))
        code.append(Path.CLOSEPOLY)
        return code

    def _calculate_points(self):
        p = get_points_between(self.start,
                               self.end,
                               self.no_of_cuts,
                               self.cut_depth,
                               self.cut_direction)
        p.append(self.start)
        self._options = self.object.options
        return Path(p, self.simple_connect(p))

    def get(self):
        p = self._calculate_points()
        return patches.PathPatch(p, **self.options)


def get_points_between(start, end, cuts, depth, direction):
    x1, y1 = start
    x2, y2 = end

    x = np.linspace(x1, x2, cuts + 1)
    y = np.linspace(y1, y2, cuts + 1)

    points = []

    for i in range(len(x))[:-1]:
        points.append((x[i], y[i]))
        tx, ty = _get_cut_point((x[i], y[i]), (x[i + 1], y[i + 1]),
                                depth,
                                direction=direction)
        points.append((tx, ty))

    points.append((x[-1], y[-1]))
    return points


def _get_cut_point(p1, p2, height, direction="out"):
    x1, y1 = p1
    x2, y2 = p2

    factor = 1
    if direction == "in":
        factor = -1

    if x2 - x1 == 0:
        return x1 + factor * height, (y1 + y2) / 2

    # Find slope
    slope = (y2 - y1) / (x2 - x1)

    if slope == 0:
        return (x1 + x2) / 2, y1 + factor * height

    # Perpendicular line slope
    slope = -1 / slope

    # Mid point will be on that line
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2

    # Find C intercept of this line
    c = mid_y - (slope * mid_x)

    # After solving equation for slop and circle
    x = mid_x + height * factor / (np.sqrt(np.square(slope) + 1))
    y = x * slope + c

    return x, y


class Triangle:
    def __init__(self, x, y, width, height, rotation=0, **kwargs):
        self._x = x
        self._y = y
        self._height = height
        self._width = width
        self._rotation = rotation
        self._options = kwargs

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def height(self):
        return self._height

    @property
    def width(self):
        return self._width

    @property
    def rotation(self):
        return self._rotation

    @property
    def options(self):
        if "color" not in self._options.keys():
            self._options["color"] = palette.blue()
        return self._options

    def _get_rect(self):
        return patches.Rectangle((self.x, self.y), self.width, self.height,
                                 self.rotation)

    def get(self):
        p = self._get_rect()
        vert = p.get_verts()
        t1 = vert[2]
        t2 = vert[3]
        vert = [x for x in vert[:2]]
        vert.append(np.asarray([(t1[0] + t2[0]) / 2, (t1[1] + t2[1]) / 2]))
        vert.append(vert[0])
        return patches.Polygon(vert, **self.options)


class Circle:
    def __init__(self, x, y, width, height, rotation=0, **kwargs):
        self._x = x
        self._y = y
        self._height = height
        self._width = width
        self._rotation = rotation
        self._options = kwargs

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def height(self):
        return self._height

    @property
    def width(self):
        return self._width

    @property
    def rotation(self):
        return self._rotation

    @property
    def options(self):
        if "color" not in self._options.keys():
            self._options["color"] = palette.blue()
        return self._options

    def _get_rect(self):
        return patches.Rectangle((self.x, self.y), self.width, self.height,
                                 self.rotation)

    @staticmethod
    def _get_diagonal_mid(points):
        p1, p2, p3, p4 = points

        m1 = (p3[1] - p1[1]) / (p3[0] - p1[0])
        m2 = (p4[1] - p2[1]) / (p4[0] - p2[0])

        c1 = p3[1] - m1 * p3[0]
        c2 = p4[1] - m2 * p4[0]

        x = (c2 - c1) / (m1 - m2)
        y = m1 * x + c1

        return x, y

    def get(self):
        verts = self._get_rect().get_verts()
        x, y = self._get_diagonal_mid(verts[:-1])
        return patches.Ellipse((x, y),
                               self.width,
                               self.height,
                               self.rotation,
                               **self.options)


def run():
    fig, ax = plt.subplots()
    p = Circle(0, 0, 1, 1)
    p2 = Rectangle(0, 0, 1, 1, fill=False)
    ax.add_patch(p.get())
    ax.add_patch(p2.get())
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    ax.axhline(0)
    ax.axvline(0)

    plt.show()
