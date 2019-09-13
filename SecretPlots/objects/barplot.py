#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 12/09/19, 10:26 AM
#
#
# All bargraph related classes


from matplotlib.patches import Patch

from SecretPlots.objects.base import Base


class BarPlot(Base):

    def __init__(self, data,
                 labels=None,
                 width=0.8,
                 gap: float = 1,
                 group_gap: float = 0.2,
                 swap_axis: bool = None,
                 boundary: bool = False,
                 boundary_color=None,
                 boundary_options=None,
                 color=None,
                 group_labels=None,
                 missing: bool = False,
                 show_legends: bool = False,
                 legends_options=None,
                 missing_options=None):
        super().__init__(data)

        self.positions = []
        self.width = width
        self.additional_options = {}
        self.gap = gap
        self.group_gap = group_gap
        self.missing = missing
        self.boundary = boundary
        self.boundary_color = boundary_color or self.palette.gray(shade=30)
        self.boundary_options = boundary_options
        self.missing_options = missing_options
        self.show_legend = show_legends
        self.legend_options = legends_options

        self._group_labels = group_labels
        self._labels = labels
        self._color = color
        self._last_location = 0
        self._sample_boundaries = []
        self._flatten_values = []
        self._flatten_samples = []
        self._flatten_groups = []
        self._flatten_missing = []
        self._boundary_start = 0
        self._swap_axis = swap_axis

    def add_options(self, **kwargs):
        self.additional_options = kwargs

    @property
    def colors(self):
        if self.no_of_groups > 0:
            if self.no_of_groups > len(self.palette.get_color_list):
                return self.palette.random(no_of_colors=self.no_of_groups)
            else:
                return self.palette.get_color_list[:self.no_of_groups]
        else:
            return [self.palette.ultramarine()] * self.no_of_samples

    @property
    def swap_axis(self):
        return self._swap_axis or False

    @property
    def labels(self):
        print(self._flatten_samples)
        if self._labels is None:
            if self.no_of_groups > 0:
                self._labels = ["Sample {}".format(x + 1) for x in
                                self._flatten_samples]
            else:
                self._labels = ["Sample {}".format(x + 1) for x in
                                self._flatten_samples]

        return self._labels

    @labels.setter
    def labels(self, values: list):
        self._labels = values

    @property
    def ticks(self):
        return [(x[0] + x[1]) / 2 for x in self._sample_boundaries]

    @property
    def group_labels(self):
        if self._group_labels is None:
            self._group_labels = ["Group {}".format(x + 1) for x in range(
                self.no_of_groups)]
        return self._group_labels

    def _customize(self, data, positions):
        options = {
            "width": self.width
        }
        options = {**options, **self.additional_options}

        if self.swap_axis:
            self.p.barh(positions, data, **options)
        else:
            self.p.bar(positions, data, **options)

    def _update_last(self, sample_change=False):
        self._last_location += self.width
        if sample_change:
            self._last_location += self.gap - self.width
        else:
            self._last_location += self.group_gap

    def _complete_boundary(self):
        self._sample_boundaries.append(
            (self._boundary_start - self.width / 2,
             self._last_location + self.width / 2))

    def _update_flatten_values(self, item, sample, group):

        if len(self.positions) > 0:
            if item is not None or self.missing:
                if sample == self._flatten_samples[-1]:
                    self._update_last()
                else:
                    self._complete_boundary()
                    self._update_last()
                    if self.no_of_groups > 0:
                        self._update_last(True)

                    self._boundary_start = self._last_location

        if item is not None or self.missing:

            if item is None:
                self._flatten_missing.append(1)
                self._flatten_values.append(0)
            else:
                self._flatten_missing.append(0)
                self._flatten_values.append(item)
            self._flatten_samples.append(sample)
            if group is not None:
                self._flatten_groups.append(group)
            self.positions.append(self._last_location)

    def _flatten(self):

        if self.no_of_samples == 1:
            if self.no_of_groups == 0:
                for i, d in enumerate(self.data):
                    self._update_flatten_values(d, i, None)
                self._complete_boundary()
            else:
                for g, d in enumerate(self.data[0]):
                    self._update_flatten_values(d, 0, g)
                self._complete_boundary()

        else:
            for i, s in enumerate(self.data):
                for g, d in enumerate(s):
                    self._update_flatten_values(d, i, g)
            self._complete_boundary()

    def _draw_boundaries(self):
        for s in self._sample_boundaries:
            opts = {"color": self.boundary_color, "alpha": 0.5}
            if self.boundary_options is not None:
                opts = {**opts, **self.boundary_options}
            self.p.axvspan(s[0], s[1], **opts)

    def _draw_missing(self):
        opts = {
            "alpha": 0.4,
            "hatch": "/",
            "color": self.palette.gray(),
            "fill": False
        }
        if self.missing_options is not None:
            opts = {**opts, **self.missing_options}

        for i, s in enumerate(self._flatten_missing):
            if s == 1:
                self.p.axvspan(self.positions[i] - self.width / 2,
                               self.positions[i] + self.width / 2, **opts)

    def _draw_axis(self):
        if self.swap_axis:
            self.p.yticks(self.ticks, self.labels)
        else:
            self.p.xticks(self.ticks, self.labels)

    def _draw_legends(self):
        if self.legend_options is None:
            self.legend_options["loc"] = "center left"
            self.legend_options["bbox_to_anchor"] = (1, 0.5)
        self.legend_options["handles"] = self.get_legend_patches()
        self.p.legend(**self.legend_options)

    def draw_boundaries(self, **kwargs):
        self.boundary = True
        self.boundary_options = kwargs

    def draw_missing(self, **kwargs):
        self.missing = True
        self.missing_options = kwargs

    def legend(self, **kwargs):
        self.show_legend = True
        self.legend_options = kwargs

    def get_raw(self):
        return self.p

    def get_legend_patches(self):
        patches = []
        for i in range(self.no_of_groups):
            patches.append(Patch(facecolor=self.colors[i],
                                 label=self.group_labels[i]))

        if self.no_of_groups == 0:
            patches.append(Patch(facecolor=self.colors[0], label=self.labels[
                0]))

        if self.missing and sum(self._flatten_missing) > 0:
            opts = {
                "hatch": "/",
                "fill": False,
                "color": self.palette.gray(),
                "label": "Missing"
            }
            if self.missing_options is not None:
                opts = {**opts, **self.missing_options}
            patches.append(Patch(**opts))

        return patches

    def customize(self):
        options = {
            "width": self.width,
            "color": self.colors[0]
        }
        for i in range(len(self._flatten_values)):
            if len(self._flatten_groups) != 0:
                options["color"] = self.colors[self._flatten_groups[i]]
            self.p.bar(
                self.positions[i],
                self._flatten_values[i],
                **options)

    def draw(self):
        self._flatten()
        if self.boundary:
            self._draw_boundaries()
        if self.missing:
            self._draw_missing()
        if self.show_legend:
            self._draw_legends()
        self.customize()
        self._draw_axis()

    def show(self):
        self.draw()
        self.p.show()


def run():
    data = [[5,  4, 8], [9, 7]]
    b = BarPlot(data)
    b.show()
