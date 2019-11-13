#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/12/19, 4:26 PM
#
#
# Network assembler

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from SecretPlots.assemblers import Assembler
from SecretPlots.constants.graph import PLOT_NETWORK
from SecretPlots.managers import LocationManager, NetworkLocation
from SecretPlots.utils import Log


class Node:
    def __init__(self, name):
        self.name = name
        self._input = []
        self._output = []
        self.row = None
        self.column = None

    def add_input(self, link):
        self._input.append(link)

    def add_output(self, link):
        self._output.append(link)

    @property
    def pos(self):
        return self.row, self.column

    @property
    def inputs(self):
        return self._input

    @property
    def outputs(self):
        return self._output

    @property
    def max_links(self):
        i = len(self.inputs)
        o = len(self.outputs)
        return i if i > o else o


class NodeInteractions:
    def __init__(self, data, log: Log):
        self._log = log
        self.data = data
        self._nodes_info = None
        self._input = "input"
        self._output = "output"
        self._log.info("Node interactions initialized")
        self.stem = 0.2
        self.stem_increment = 0.1
        self.columns = None
        self.width = 1
        self.height = 0.5
        self.row_distance = 1

    def _extract(self):
        all_info = {}

        for d in self.data:
            if d[0] in all_info.keys():
                all_info[d[0]].add_output(d)
            else:
                all_info[d[0]] = Node(d[0])
                all_info[d[0]].add_output(d)

            if d[1] in all_info.keys():
                all_info[d[1]].add_input(d)
            else:
                all_info[d[1]] = Node(d[1])
                all_info[d[1]].add_input(d)

        info_list = []
        for a in all_info.values():
            info_list.append((a.name, a))

        info_list = sorted(info_list,
                           key=lambda x: x[1].max_links,
                           reverse=True)

        self._log.info(f"Total of {len(info_list)} nodes found")
        if self.columns is None:
            self.columns = np.floor(np.sqrt(len(info_list)))
            self._log.info(f"Auto-Columns : {len(info_list)}")

        r, c = 0, 0
        for k in info_list:
            k[1].row = r
            k[1].column = c
            if c == (self.columns - 1):
                c = 0
                r += 1
            else:
                c += 1

        self._nodes_info = info_list

    @property
    def nodes(self):
        if self._nodes_info is None:
            self._extract()
        return self._nodes_info


class NetworkAssembler(Assembler):

    def __init__(self, fig: plt.Figure, log: Log):
        super().__init__(fig, log)
        self._interactions = None

    @property
    def interactions(self):
        if self._interactions is None:
            self._interactions = NodeInteractions(self.data.raw_data,
                                                  self._log)
        return self._interactions

    def _adjust_defaults(self):
        self.am.frame_visibility = (0, 0, 0, 0)
        self.am.x.show_ticks = False
        self.am.y.show_ticks = False

    @property
    def main_location_manager(self) -> LocationManager:
        return NetworkLocation(self.am, self.om, self._log)

    @property
    def type(self):
        return PLOT_NETWORK

    def _draw_elements(self):
        self.em.show_values = True
        self.om.width = self.interactions.width
        self.om.height = self.interactions.height

        count = 0
        for i, e in enumerate(self.interactions.nodes):
            r, c = e[1].pos
            sx = r + r * 1
            sy = c + c * 1
            shape = self.om.get(sx, sy, 0, (i, 0))

            lx = shape.x
            ly = shape.y + shape.height

            for out in np.linspace(lx, lx + shape.width,
                                   len(e[1].outputs) + 2)[1:-1]:
                line = Line2D([out, out],
                              [ly, ly + self.interactions.stem],
                              color=shape.color)
                self.ax.add_line(line)
            self.ax.add_patch(shape.get())
            self.em.draw_values(shape, e[0], shape.color)
            count += shape.width + 1

    def draw(self):
        # self._adjust_defaults()
        self._draw_elements()
        self._draw_axis()
