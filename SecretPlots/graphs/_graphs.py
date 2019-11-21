#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 7:57 PM
#
#
#
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 05/10/19, 11:03 AM
#
#
# Main graph class

import matplotlib.pyplot as plt

from SecretPlots.assemblers import Assembler
from SecretPlots.utils import Log


class SecretPlot:
    def __init__(self, data, fig: plt.Figure = None, log: Log = None):
        if fig is None:
            fig = plt.figure()
        self.fig = fig
        self._raw_data = data
        if log is None:
            log = Log()
        self._log = log
        self._assembler = None
        self._figure_drawn = False

        self.orientation = None
        self.x_gap = None
        self.y_gap = None
        self.x_ticks = None
        self.y_ticks = None
        self.x_label = None
        self.y_label = None
        self.x_ticklabels = None
        self.y_ticklabels = None
        self.x_padding_start = None
        self.x_padding_end = None
        self.y_padding_start = None
        self.y_padding_end = None
        self.group_gap = None
        self.colors = None
        self.cmap = None
        self.cmap_location = None
        self.show_cmap = None
        self.show_legend = None
        self.width = None
        self.height = None
        self.shape = None
        self.show_x_midlines = None
        self.show_y_midlines = None
        self.show_x_edgelines = None
        self.show_y_edgelines = None
        self.show_values = None
        self.show_grid = None
        self.x_inverted = None
        self.y_inverted = None
        self.on_color = None
        self.off_color = None

        self._log.info(
            "'{}' initialization complete ".format(self.assembler.type))

    def _check_settings(self):
        if self.orientation is not None:
            self.assembler.am.orientation = self.orientation
        if self.x_gap is not None:
            self.x.gap = self.x_gap
        if self.y_gap is not None:
            self.y.gap = self.y_gap
        if self.group_gap is not None:
            self.assembler.am.group_gap = self.group_gap
        if self.colors is not None:
            if isinstance(self.colors, str):
                self.colors = [self.colors]
            self.assembler.cm.user_colors = self.colors
        if self.cmap is not None:
            self.assembler.cm.user_cmap = self.cmap

        self.assembler.gm.has_colorbar = self.show_cmap
        self.assembler.gm.colorbar_location = self.cmap_location
        self.assembler.em.show_legends = self.show_legend
        self.assembler.am.x.label = self.x_label
        self.assembler.am.y.label = self.y_label

        if self.width is not None:
            self.assembler.om.width = self.width
        if self.height is not None:
            self.assembler.om.height = self.height
        if self.shape is not None:
            self.assembler.om.shape = self.shape
        if self.show_values is not None:
            self.assembler.em.show_values = self.show_values
        if self.show_grid is not None:
            self.assembler.em.show_grid = self.show_grid

        if self.show_x_midlines is not None:
            self.assembler.am.x.show_midlines = self.show_x_midlines
        if self.show_y_midlines is not None:
            self.assembler.am.y.show_midlines = self.show_y_midlines
        if self.show_x_edgelines is not None:
            self.assembler.am.x.show_edgelines = self.show_x_edgelines
        if self.show_y_edgelines is not None:
            self.assembler.am.y.show_edgelines = self.show_y_edgelines

        if self.x_ticklabels is not None:
            self.assembler.am.x.tick_labels = self.x_ticklabels
        if self.y_ticklabels is not None:
            self.assembler.am.y.tick_labels = self.y_ticklabels
        if self.x_ticks is not None:
            self.assembler.am.x.ticks = self.x_ticks
        if self.y_ticks is not None:
            self.assembler.am.y.ticks = self.y_ticks

        if self.x_inverted is not None:
            self.assembler.am.x.is_inverted = self.x_inverted
        if self.y_inverted is not None:
            self.assembler.am.y.is_inverted = self.y_inverted

        if self.on_color is not None:
            self.assembler.cm.on_color = self.on_color
        if self.off_color is not None:
            self.assembler.cm.off_color = self.off_color

        if self.x_padding_start is not None:
            self.assembler.am.x.padding_start = self.x_padding_start
        if self.x_padding_end is not None:
            self.assembler.am.x.padding_end = self.x_padding_end
        if self.y_padding_start is not None:
            self.assembler.am.y.padding_start = self.y_padding_start
        if self.y_padding_end is not None:
            self.assembler.am.y.padding_end = self.y_padding_end

    @property
    def main_assembler(self) -> Assembler:
        raise NotImplementedError

    @property
    def x(self):
        return self.assembler.am.x

    @property
    def y(self):
        return self.assembler.am.y

    @property
    def ax(self) -> plt.Axes:
        return self.assembler.am.ax

    @property
    def assembler(self):
        if self._assembler is None:
            self._assembler = self.main_assembler
            self._assembler.data = self._raw_data
        return self._assembler

    def _assemble_components(self):
        self._check_settings()
        self.assembler.draw()

    def draw(self):
        if self._figure_drawn:
            return
        self._assemble_components()
        self._figure_drawn = True

    def show(self, tight=False):
        self.draw()
        if tight:
            plt.tight_layout()
        plt.show()

    def save(self, filename, **kwargs):
        self.draw()
        plt.savefig(filename, **kwargs)

    def add_grid(self, **kwargs):
        self.show_grid = True
        self.assembler.em.add_grid_options(**kwargs)
        return self

    def add_values(self, **kwargs):
        self.show_values = True
        self.assembler.em.add_value_options(**kwargs)
        return self

    def add_legends(self, **kwargs):
        self.show_legend = True
        self.assembler.em.add_legends_options(**kwargs)
        return self

    def add_x_ticklabels(self, labels, **kwargs):
        self.x_ticklabels = labels
        self.assembler.am.x.add_ticklabels_options(**kwargs)
        return self

    def add_y_ticklabels(self, labels, **kwargs):
        self.y_ticklabels = labels
        self.assembler.am.y.add_ticklabels_options(**kwargs)
        return self

    def add_x_gap(self, value):
        self.x_gap = value
        return self

    def add_y_gap(self, value):
        self.y_gap = value
        return self

    def add_x_midlines(self, **kwargs):
        self.show_x_midlines = True
        self.assembler.am.x.add_midlines_options(**kwargs)
        return self

    def add_y_midlines(self, **kwargs):
        self.show_y_midlines = True
        self.assembler.am.y.add_midlines_options(**kwargs)
        return self

    def add_x_edgelines(self, **kwargs):
        self.show_x_edgelines = True
        self.assembler.am.x.add_edgelines_options(**kwargs)
        return self

    def add_y_edgelines(self, **kwargs):
        self.show_y_edgelines = True
        self.assembler.am.y.add_edgelines_options(**kwargs)
        return self

    def add_group_gap(self, value):
        self.group_gap = value
        return self

    def invert_x(self):
        self.x_inverted = True
        return self

    def invert_y(self):
        self.y_inverted = True
        return self

    def add_x_label(self, label, **kwargs):
        self.x_label = label
        self.assembler.am.x.add_label_options(**kwargs)
        return self

    def add_y_label(self, label, **kwargs):
        self.y_label = label
        self.assembler.am.y.add_label_options(**kwargs)
        return self

    def add_x_padding(self, start, end):
        self.x_padding_start = start
        self.x_padding_end = end
        return self

    def add_y_padding(self, start, end):
        self.y_padding_start = start
        self.y_padding_end = end
        return self

    def add_cmap(self, name=None, loc="right"):
        self.show_cmap = True
        if name is not None:
            self.cmap = name

        self.cmap_location = loc
        return self

    def add_colors(self, values):
        self.colors = values
        return self

    def add_on_color(self, value):
        self.on_color = value
        return self

    def add_off_color(self, value):
        self.off_color = value
        return self

    def change_frame_visibility(self, left, right, top, bottom):
        self.assembler.am.frame_visibility = (left, right, top, bottom)
        return self

    def change_shape(self, value):
        self.shape = value
        return self

    def change_orientation(self, value):
        self.orientation = value
        return self

    def change_aspect_ratio(self, value):
        self.assembler.am.aspect_ratio = value
        return self

    def remove_cmap(self):
        self.show_cmap = False
        return self

    def remove_x_ticks(self):
        self.assembler.am.x.show_ticks = False
        return self

    def remove_y_ticks(self):
        self.assembler.am.y.show_ticks = False

    def remove_frame(self):
        self.assembler.am.frame_visibility = (0, 0, 0, 0)
        return self
