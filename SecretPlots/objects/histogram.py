# SecretPlots 2019
# Author : Rohit Suratekar
# Date : 5 September 2019
#
# Histogram Object

import functools
import operator

import matplotlib.pylab as plt
import numpy as np
from SecretColors import Palette
from matplotlib.patches import Patch


class Histogram:
    def __init__(self):
        self.palette = Palette()
        self._c = plt

    def basic(self, data):
        self._c.hist(data)
        self._c.ylabel("Frequency")


class BoxPlot:
    def __init__(self, data,
                 width: float = 0.5,
                 gap_between_samples: float = 0.5,
                 gap_between_groups: float = 0.1,
                 plot_missing=False,
                 shadow=True,
                 labels=None,
                 shadow_color=None,
                 shadow_alpha=0.4,
                 group_labels=None,
                 vert: bool = True,
                 legend_loc=0):

        self.palette = Palette()
        self._ = plt
        self.data = data
        self.__no_of_samples = 0
        self.__no_of_groups = 0
        self.__last_position = 0
        self.__group_colors = []
        self.__sample_boundaries = []
        self.__locations = []
        self.legend_loc = legend_loc
        self.medianprops = dict(color=self.palette.black())
        self.plot_missing = plot_missing
        self.shadow = shadow
        self.__labels = labels
        self.__group_labels = group_labels
        self.shadow_color = shadow_color or self.palette.gray(shade=30)
        self.shadow_alpha = shadow_alpha
        self.width = width
        self.vert = vert
        self.gap_between_samples = gap_between_samples
        self.gap_between_group = gap_between_groups

        self.__calculate_dimensions()

    @property
    def no_of_samples(self):
        return self.__no_of_samples

    @property
    def no_of_groups(self):
        return self.__no_of_groups

    @property
    def group_colors(self):
        return self.__group_colors

    @group_colors.setter
    def group_colors(self, colors: list):
        self.__group_colors = colors

    @property
    def group_labels(self):
        if self.__group_labels is None:
            self.__group_labels = ["Group {}".format(x + 1) for x in range(
                self.no_of_groups)]
        return self.__group_labels

    @property
    def sample_boundaries(self):
        return self.__sample_boundaries

    @property
    def labels(self):
        if self.__labels is None:
            self.__labels = ["Sample {}".format(x + 1) for x in range(
                self.no_of_samples)]
        return self.__labels

    @property
    def ticks(self):
        return [(x[0] + x[1]) / 2 for x in self.sample_boundaries]

    def get_legend_patches(self):
        patches = []
        for i in range(self.no_of_groups):
            patches.append(Patch(facecolor=self.group_colors[i],
                                 label=self.group_labels[i]))

        return patches

    def legend(self, **kwargs):
        if len(kwargs) == 0:
            kwargs["bbox_to_anchor"] = (1, 1)
        kwargs["handles"] = self.get_legend_patches()
        self._.legend(**kwargs)

    @property
    def get_stat(self):
        d = functools.reduce(operator.concat, self.data)
        d = [list(x) for x in d if x is not None]
        d = functools.reduce(operator.concat, d)

        return {"average": sum(d) / len(d),
                "min": min(d),
                "max": max(d)}

    def __calculate_dimensions(self):
        try:
            temp = [x for x in self.data if x is not None]
            iter(temp[0])
            try:
                temp2 = [x for x in temp[0] if x is not None]
                iter(temp2[0])
                self.__no_of_groups = max([len(x) for x in self.data])
                self.__no_of_samples = len(self.data)
            except TypeError:
                self.__no_of_groups = len(self.data)
                self.__no_of_samples = 1
        except TypeError:
            self.__no_of_groups = 0
            self.__no_of_samples = 1

        if self.no_of_groups > 1:
            if self.no_of_groups > len(self.palette.get_color_list):
                self.__group_colors = self.palette.random(self.no_of_groups)
            else:
                self.__group_colors = self.palette.get_color_list[
                                      :self.no_of_groups]

    @property
    def get_plot(self):
        return self._

    def __design(self, data, location: float, color=None):
        boxprops = {}
        medianprops = self.medianprops
        if color is not None:
            boxprops['facecolor'] = color

        self._.boxplot(data,
                       vert=self.vert,
                       patch_artist=True,
                       boxprops=boxprops,
                       medianprops=medianprops,
                       widths=self.width,
                       positions=[location])

    def __plot_missing(self):
        self.__locations.append(self.__last_position)
        start = self.__last_position - self.width / 2
        end = self.__last_position + self.width / 2
        options = {
            "alpha": 0.4,
            "hatch": "//",
            "color": self.palette.gray(),
            "fill": False
        }

        if self.vert:
            self._.axvspan(start, end, **options)
        else:
            self._.axhspan(start, end, **options)

        self.__last_position += self.width
        self.__last_position += self.gap_between_group

    def __plot_shadow(self):

        options = {
            "color": self.shadow_color,
            "alpha": self.shadow_alpha
        }

        for b in self.sample_boundaries:
            if self.vert:
                self._.axvspan(b[0], b[1], **options)
            else:
                self._.axhspan(b[0], b[1], **options)

    def __plot_ticks(self):
        if self.vert:
            self._.xticks(self.ticks, self.labels)
        else:
            self._.yticks(self.ticks, self.labels)

    def __plot_groups(self, data):

        b1 = self.__last_position - self.width / 2
        for i in range(len(data)):
            if data[i] is None:
                if self.plot_missing:
                    self.__plot_missing()
                continue
            self.__locations.append(self.__last_position)
            self.__design(data[i], self.__last_position, self.group_colors[i])
            self.__last_position += self.width
            self.__last_position += self.gap_between_group

        b2 = self.__last_position - self.gap_between_group - self.width / 2
        self.__sample_boundaries.append((b1, b2))
        self.__last_position += self.gap_between_samples

    def plot(self):

        if self.no_of_samples == 1:
            if self.no_of_groups < 2:
                self.__design(self.data, 0, color=self.palette.red())
                self.__sample_boundaries.append(
                    (0 - self.width / 2, self.width / 2))
            else:
                self.__plot_groups(self.data)
        else:
            for s in self.data:
                self.__plot_groups(s)

        self.__plot_ticks()
        self.__plot_shadow()

    def show(self):
        self._.show()

    def tight(self, **kwargs):
        self._.tight_layout(**kwargs)

    def redraw(self):
        self._.cla()
        self._.clf()
        self._.close()
        self.__group_colors = []
        self.__sample_boundaries = []
        self.__locations = []
        self.__calculate_dimensions()
        self.plot()


def run():
    d = np.random.uniform(1, 100, 10)
    e = np.random.uniform(40, 80, 10)
    bb = BoxPlot([[d, e, None], [e, e, d]])
    bb.plot()
    bb.show()
