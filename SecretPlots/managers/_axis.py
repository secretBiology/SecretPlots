#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 8:04 PM
#
#
# Axis Manager

from SecretPlots.objects import Axis
from SecretPlots.utils import Log


class AxisManager:
    def __init__(self, gm, log: Log):
        self.gm = gm
        self._log = log

        self._orientation = None
        self._x = None
        self._y = None
        self._ax = None
        self.is_reversed = False
        self.aspect_ratio = None
        self.group_gap = 1
        self._frame_visibility = None

        self._log.info("AxisManager is initialized with default values")

    @property
    def frame_visibility(self):
        if self._frame_visibility is None:
            self._frame_visibility = (1, 1, 1, 1)
        return self._frame_visibility

    @frame_visibility.setter
    def frame_visibility(self, value):
        if type(value) == bool:
            if value:
                self._frame_visibility = (1, 1, 1, 1)
            else:
                self._frame_visibility = (0, 0, 0, 0)
        elif type(value) == tuple:
            if len(value) == 4:
                self._frame_visibility = value
            else:
                self._log.error("Frame visibility should be either Bool or "
                                "tuple with length 4 (left, right, top , "
                                "bottom)")

    @property
    def orientation(self):
        if self._orientation is None:
            self._orientation = "x"
        return self._orientation.replace("-", "").replace("+", "")

    @orientation.setter
    def orientation(self, value: str):
        value = value.strip().lower()
        if value.replace("-", "").replace("+", "") not in ["x", "y"]:
            self._log.error("Invalid axis orientation. Allowed orientations "
                            "are x, y, -x, -y")

        self._orientation = value
        self._log.info("Axis orientation set to : {}".format(value))

        if self._orientation == "-x":
            self.y.is_inverted = True
        elif self._orientation == "-y":
            self.x.is_inverted = True

    @property
    def is_reflected(self):
        return "-" in self.orientation

    @property
    def ax(self):
        if self._ax is None:
            self._ax = self.gm.get_main_axis()
        return self._ax

    @property
    def x(self):
        if self._x is None:
            self._x = Axis("x", 0, self._log)
        return self._x

    @property
    def y(self):
        if self._y is None:
            self._y = Axis("y", 1, self._log)
        return self._y

    @property
    def major(self):
        if self.orientation == "x":
            return self.x
        else:
            return self.y

    @property
    def minor(self):
        if self.orientation == "x":
            return self.y
        else:
            return self.x
