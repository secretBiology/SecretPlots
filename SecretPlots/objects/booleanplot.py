#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 18/09/19, 10:22 AM
#
#
#  This is special plotting class created to visualize the Boolean Model
#  results

import matplotlib.lines as lines
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from SecretColors import Palette

from SecretPlots.objects.shapes import *

ON_COLOR = Palette().lime(shade=40)
OFF_COLOR = Palette().lime(shade=70)
HIGHLIGHTED_ITEM = 3


class BooleanObject:
    def __init__(self,
                 data,
                 threshold: float = 1,
                 height: float = 1,
                 width: float = 2,
                 gap: float = 0.1,
                 vertical_gap=None,
                 horizontal_gap=None):
        self._data = data
        self.threshold = threshold
        self._locations = []
        self._width = width
        self._height = height
        self._rows = 0
        self._columns = 0
        self._orientation = "x"
        if vertical_gap is None:
            vertical_gap = gap
        if horizontal_gap is None:
            horizontal_gap = gap
        self.vertical_gap = vertical_gap
        self.horizontal_gap = horizontal_gap

    @property
    def rows(self):
        return self._rows

    @property
    def columns(self):
        return self._columns

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def data(self):
        return self._data

    @property
    def locations(self):
        return self._locations

    def _convert_data(self):
        self._data = np.asarray(self._data)
        self._data[self._data < self.threshold] = 0
        self._data[self._data >= self.threshold] = 1

    def _assign_locations(self):
        try:
            self._rows = self.data.shape[1]
            self._columns = self.data.shape[0]
        except IndexError:
            self._columns = 1
            self._rows = self.data.shape[0]

        if self._columns == 1:
            baseline = 0
            for x in self.data:
                self._locations.append((0, baseline))
                baseline += self.height + self.vertical_gap
        else:
            start = 0
            for i in range(len(self.data)):
                temp = []
                baseline = 0
                for x in self.data[i]:
                    temp.append((start, baseline))
                    baseline += self.height + self.vertical_gap
                self._locations.append(temp)
                start += self.width + self.horizontal_gap

    def get(self):
        self._convert_data()
        self._assign_locations()

        items = []
        if self.columns == 1:
            for i, d in enumerate(self.data):
                items.append((d, Rectangle(self.locations[i],
                                           self.height,
                                           width=self.width,
                                           axis=self._orientation)))

        else:
            for i, d in enumerate(self.data):
                for j, x in enumerate(d):
                    items.append((
                        x, Rectangle(self.locations[i][j],
                                     self.height,
                                     width=self.width,
                                     axis=self._orientation)
                    ))
        return items


class BooleanAxis:
    def __init__(self,
                 obj: BooleanObject,
                 on_color=ON_COLOR,
                 off_color=OFF_COLOR,
                 gap=0.1,
                 vertical_gap=None,
                 horizontal_gap=None,
                 group_labels=None,
                 sample_labels=None,
                 xlines=False,
                 ylines=False,
                 show_legend=True,
                 legend_options=None

                 ):

        if vertical_gap is None:
            vertical_gap = gap
        if horizontal_gap is None:
            horizontal_gap = gap

        self.vertical_gap = vertical_gap
        self.horizontal_gap = horizontal_gap

        obj.vertical_gap = vertical_gap
        obj.horizontal_gap = horizontal_gap

        self.items = obj.get()
        # Get rows and columns after get()
        self.rows = obj.rows
        self.cols = obj.columns

        self.on_color = on_color
        self.off_color = off_color
        self.xlines = xlines
        self.ylines = ylines

        self._sample_labels = sample_labels
        self._group_labels = group_labels
        self._closest_point = None
        self._farthest_point = None
        self._highlights = {}
        self._show_legend = show_legend
        self._legend_options = legend_options

    @property
    def sample_labels(self):
        if self._sample_labels is None:
            return ["Sample {}".format(x) for x in range(self.cols)]
        return self._sample_labels

    @sample_labels.setter
    def sample_labels(self, labels: list):
        self._sample_labels = labels

    @property
    def group_labels(self):
        if self._group_labels is None:
            return ["Group {}".format(x) for x in range(self.rows)]
        return self._group_labels

    @group_labels.setter
    def group_labels(self, labels: list):
        self._group_labels = labels

    @property
    def xticks(self):
        temp = {}  # Fake dictionary to get unique values
        for m in self.items:
            temp[m[1].x + m[1].width / 2] = True
        return list(temp.keys())

    @property
    def yticks(self):
        temp = {}  # Fake dictionary to get unique values
        for m in self.items:
            temp[m[1].y + m[1].height / 2] = True
        return list(temp.keys())

    def _add_group_labels(self, ax):
        y_labels = self.group_labels
        for i, y in enumerate(self.yticks):
            ax.text(self._closest_point.x, y,
                    "{} -".format(y_labels[i]),
                    ha="right",
                    va="center")

    def _set_axis(self, ax):
        e1 = [(x[1].x, x[1].y) for x in self.items]
        e1_dis = [np.sqrt(sum(np.square(x))) for x in e1]

        self._closest_point = self.items[e1_dis.index(min(e1_dis))][1]
        self._farthest_point = self.items[e1_dis.index(max(e1_dis))][1]

        ax.set_xlim(self._closest_point.x - 1,
                    self._farthest_point.x + self._farthest_point.width)
        ax.set_ylim(self._closest_point.y, self._farthest_point.y +
                    self._farthest_point.height)

        ax.yaxis.set_ticks([])
        ax.xaxis.set_ticks(self.xticks)
        ax.xaxis.set_ticklabels(self.sample_labels, rotation=45, ha="left")
        ax.set_aspect("equal")
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.xaxis.tick_top()
        self._add_group_labels(ax)

    @staticmethod
    def _get_line(x_points, y_points):
        return lines.Line2D(
            x_points, y_points,
            color="k",
            alpha=0.5,
        )

    def _draw_lines(self, ax):

        if self.xlines:
            for x in self.items:
                line = self._get_line(
                    [x[1].x, x[1].x + x[1].width + self.horizontal_gap],
                    [x[1].y - self.vertical_gap / 2,
                     x[1].y - self.vertical_gap / 2])

                if self._closest_point.y != x[1].y:
                    ax.add_line(line)

        if self.ylines:
            for y in self.items:
                line = self._get_line(
                    [y[1].x + y[1].width + self.horizontal_gap / 2,
                     y[1].x + y[1].width + self.horizontal_gap / 2],
                    [y[1].y, y[1].y + y[1].height + self.vertical_gap])

                if self._farthest_point.x != y[1].x:
                    ax.add_line(line)

    def highlight(self, row, column, label=None, **kwargs):

        if label is None:
            label = "Highlighted"

        loc = column * self.rows + row
        self.items[loc] = (
            self.items[loc][0] + HIGHLIGHTED_ITEM, self.items[loc][1])

        c = ON_COLOR
        if self.items[loc][0] == 0:
            c = OFF_COLOR

        if len(kwargs) == 0:
            self._highlights[loc] = {
                "ec": "k",
                "ls": "--",
                "lw": 1.5,
                "color": c,
                "secretplot": True,
                "label": label
            }
        else:
            opt = {"color": c, "label": label}
            self._highlights[loc] = {**opt, **kwargs}

    def get_patches(self, labels=None):

        group_colors = [ON_COLOR, OFF_COLOR]
        if labels is None:
            labels = ["ON", "OFF"]

        p = []
        for i in range(len(group_colors)):
            p.append(patches.Patch(
                facecolor=group_colors[i],
                label=labels[i]))

        highlight_added = False
        for key in self._highlights.keys():
            opts = self._highlights[key]

            if "secretplot" in opts.keys():
                if highlight_added:
                    continue
                highlight_added = True

            try:
                del opts["secretplot"]
            except KeyError:
                pass

            p.append(patches.Patch(**self._highlights[key]))

        return p

    def _draw_legend(self, ax):

        if not self._show_legend:
            return

        opts = {
            "handles": self.get_patches(),
            "bbox_to_anchor": (1.1, 1)
        }

        if self._legend_options is not None:
            del opts["bbox_to_anchor"]
            opts = {**opts, **self._legend_options}

        ax.legend(**opts)

    def _draw_patches(self, ax):

        for i, p in enumerate(self.items):
            opts = {
                "color": self.on_color
            }
            state = p[0]
            if p[0] > 1:
                state -= HIGHLIGHTED_ITEM

            if state == 0:
                opts["color"] = self.off_color

            if p[0] > 1:
                opts = {**opts, **self._highlights[i]}

            try:
                del opts["secretplot"]
            except KeyError:
                pass
            pp = patches.PathPatch(p[1].path, **opts)
            ax.add_patch(pp)

    def legend(self, show=True, **kwargs):
        self._show_legend = show
        if len(kwargs) != 0:
            self._legend_options = kwargs

    def draw(self, ax):
        self._draw_patches(ax)
        self._set_axis(ax)
        self._draw_lines(ax)
        self._draw_legend(ax)


def run():
    data = [np.random.uniform(1, 40, 15) for x in range(5)]
    b = BooleanObject(data, threshold=20)
    a = BooleanAxis(b, gap=0)
    fig, ax = plt.subplots()
    a.legend()
    a.draw(ax)
    plt.xlabel("Something")
    plt.tight_layout()
    plt.show()
