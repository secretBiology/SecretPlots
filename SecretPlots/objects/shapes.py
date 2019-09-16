#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 15/09/19, 3:41 PM
#
#
# All shapes


import numpy as np
from matplotlib.path import Path


class Shape:
    def __init__(self, origin, height, width, axis,
                 cuts=3,
                 cut_depth=0.2,
                 cut_outward=False,
                 cut_position=None,
                 **kwargs):
        self.x = origin[0]
        self.y = origin[1]
        self.height = height
        self.width = width
        self.axis = axis
        self.cuts = cuts
        self.cut_depth = cut_depth
        self.cut_outward = cut_outward
        self.cut_position = cut_position
        self.options = kwargs

    @property
    def path(self):
        return Path(self.vert, self.code)

    @property
    def vert(self):
        raise NotImplementedError("Must have vert property")

    @property
    def code(self):
        raise NotImplementedError("Must have code property")

    @staticmethod
    def simple_connect(vert: list):
        code = [Path.MOVETO]
        code.extend([Path.LINETO] * (len(vert) - 2))
        code.append(Path.CLOSEPOLY)
        return code


class Triangle(Shape):
    BOTTOM_POSITIONS = ["bottom", "b", "right", "r", "all", "a", "both"]

    @property
    def vert(self):
        if self.axis == "x":
            out = [(self.x, self.y),
                   (self.x + self.width / 2, self.height + self.y),
                   (self.x + self.width, self.y)]

            if self.cut_position in Triangle.BOTTOM_POSITIONS:
                out.extend(list(reversed(get_points_between(
                    (self.x + self.width, self.y),
                    (self.x, self.y),
                    self.cuts,
                    self.cut_depth,
                    self.cut_outward
                ))))
            else:
                out.append((self.x, self.y))

            return out
        else:
            if self.cut_position in self.BOTTOM_POSITIONS:
                out = get_points_between(
                    (self.x, self.y),
                    (self.x, self.y + self.width),
                    self.cuts,
                    self.cut_depth,
                    self.cut_outward
                )
            else:
                out = [(self.x, self.y)]

            out.extend(
                [(self.x, self.y + self.width),
                 (self.x + self.height, self.y + self.width / 2),
                 (self.x, self.y)]
            )
            return out

    @property
    def code(self):
        return self.simple_connect(self.vert)


class Diamond(Shape):
    @property
    def vert(self):
        if self.axis == "x":
            return [(self.x + self.width / 2, self.y),
                    (self.x, self.height / 2 + self.y),
                    (self.x + self.width / 2, self.height + self.y),
                    (self.x + self.width, self.height / 2 + self.y),
                    (self.x, self.y)]
        else:
            return [(self.x, self.y + self.width / 2),
                    (self.x + self.height / 2, self.y + self.width),
                    (self.x + self.height, self.y + self.width / 2),
                    (self.x + self.height / 2, self.y),
                    (self.x, self.y + self.width / 2)]

    @property
    def code(self):
        return self.simple_connect(self.vert)


def get_points_between(start, end, cuts, size, direction):
    out = []
    i = 1
    j = 0
    if start[1] == end[1]:
        i = 0
        j = 1

    if start[i] > end[i]:
        start, end = end, start

    points = []
    for p in np.linspace(start[i], end[i], cuts + 1):
        temp = [None, None]
        temp[i] = p
        temp[j] = start[j]
        points.append((temp[0], temp[1]))

    for m in range(0, len(points) - 1):
        out.append(points[m])
        loc = abs(points[m][i] - points[m + 1][i]) / 2
        loc += points[m][i]
        temp = [None, None]
        temp[i] = loc
        if direction:
            temp[j] = points[m][j] + size
        else:
            temp[j] = points[m][j] - size
        out.append((temp[0], temp[1]))

    out.append(points[-1])

    return out


class Rectangle(Shape):
    TOP_POSITIONS = ["top", "t", "left", "l", "all", "a", "both"]
    BOTTOM_POSITIONS = ["bottom", "b", "right", "r", "all", "a", "both"]

    @property
    def vert(self):
        if self.axis == "x":
            out = [(self.x, self.y), (self.x, self.height + self.y)]
            if self.cut_position in Rectangle.TOP_POSITIONS:
                out.extend(get_points_between(
                    (self.x, self.height + self.y),
                    (self.x + self.width, self.height + self.y),
                    self.cuts,
                    self.cut_depth,
                    self.cut_outward
                ))
            else:
                out.append((self.x + self.width, self.height + self.y))

            if self.cut_position in Rectangle.BOTTOM_POSITIONS:
                out.extend(list(reversed(get_points_between(
                    (self.x + self.width, self.y),
                    (self.x, self.y),
                    self.cuts,
                    self.cut_depth,
                    not self.cut_outward
                ))))
            else:
                out.append((self.x + self.width, self.y))

            out.append((self.x, self.y))

            return out
        else:
            out = []
            if self.cut_position in Rectangle.TOP_POSITIONS:
                out.extend(get_points_between(
                    (self.x, self.y),
                    (self.x, self.y + self.width),
                    self.cuts,
                    self.cut_depth,
                    not self.cut_outward
                ))
            else:
                out.extend([(self.x, self.y), (self.x, self.y + self.width)])

            out.append((self.x + self.height, self.y + self.width))

            if self.cut_position in Rectangle.BOTTOM_POSITIONS:
                out.extend(list(reversed(get_points_between(
                    (self.x + self.height, self.y + self.width),
                    (self.x + self.height, self.y),
                    self.cuts,
                    self.cut_depth,
                    self.cut_outward
                ))))
            else:
                out.append((self.x + self.height, self.y))
            out.append((self.x, self.y))

            return out

    @property
    def code(self):
        return self.simple_connect(self.vert)
