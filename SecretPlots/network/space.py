#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/13/19, 4:03 PM
#
#
from SecretPlots.utils import Log
import numpy as np


class Edge:
    def __init__(self, start, end, value, **options):
        self.start = start
        self.end = end
        self.value = value
        self.options = options


class Slots:
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"

    LOCATIONS = [
        (TOP, -1, 0),
        (BOTTOM, 1, 0),
        (RIGHT, 0, 1),
        (LEFT, 0, -1),
        (TOP_LEFT, -1, -1),
        (TOP_RIGHT, -1, 1),
        (BOTTOM_LEFT, 1, -1),
        (BOTTOM_RIGHT, 1, 1)
    ]

    def __init__(self, start_name, log: Log):
        # Reshaping to (1,1) is important for later merging
        self._log = log
        self.data = np.asanyarray([start_name]).reshape(1, 1)
        self.row = None
        self.column = None
        self._reset_stats()
        self._current_row = 0
        self._current_column = 0

        self._log.info("Slots initialized")

    @property
    def all(self) -> list:
        return list(self.data.flatten())

    def index(self, element):
        try:
            return self.all.index(element)
        except ValueError:
            self._log.warn(f"Unknown element : {element}")
            return None

    def get_row(self, index):
        return int(index / self.column)

    def get_column(self, index):
        return index % self.column

    def reset_pointer(self, element):
        i = self.index(element)
        if i is None:
            self._log.error(f"Element {element} not found", True)
        else:
            self._current_row = self.get_row(i)
            self._current_column = self.get_column(i)

    def add_pos(self, name, row, column):
        if self._current_row == 0 and row == -1:
            self._add_row(True)
            self._current_row = 1
        if self._current_row == self.row - 1 and row == 1:
            self._add_row(False)
        if self._current_column == 0 and column == -1:
            self._add_column(False)
            self._current_column = 1
        if self._current_column == self.column - 1 and column == 1:
            self._add_column(True)

        self._current_row += row
        self._current_column += column
        self.data[self._current_row, self._current_column] = name

    def add(self, name, position):

        for pos, row, col in self.LOCATIONS:
            if pos == position:
                self.add_pos(name, row, col)
                return
        self._log.error(f"Unknown position : {position}", True)

    def is_conflict(self, pos):
        def _check_none(r, c):
            return self.data[
                       self._current_row + r, self._current_column + c
                   ] is None

        if (pos in [self.TOP_RIGHT, self.TOP, self.TOP_LEFT]) and (
                self._current_row == 0):
            return False
        if (pos in [self.BOTTOM, self.BOTTOM_LEFT, self.BOTTOM_RIGHT]) and (
                self._current_row == self.row - 1):
            return False
        if (pos in [self.LEFT, self.TOP_LEFT, self.BOTTOM_LEFT]) and (
                self._current_column == 0):
            return False
        if (pos in [self.RIGHT, self.TOP_RIGHT, self.BOTTOM_RIGHT]) and (
                self._current_column == self.column - 1):
            return False

        for p, row, col in self.LOCATIONS:
            if p == pos:
                return not _check_none(row, col)

        self._log.error(f"Unknown position {pos}", True)

    def _reset_stats(self):
        self.row = self.data.shape[0]
        try:
            self.column = self.data.shape[1]
        except IndexError:
            self.column = 1

    def _add_row(self, on_top: bool):
        f = np.array([None] * self.column)
        if on_top:
            self.data = np.vstack((f, self.data))
        else:
            self.data = np.vstack((self.data, f))
        self._reset_stats()

    def _add_column(self, on_right: bool):
        f = np.asanyarray([None] * self.row).reshape(self.row, 1)
        if on_right:
            self.data = np.hstack((self.data, f))
        else:
            self.data = np.hstack((f, self.data))
        self._reset_stats()

    def safely_add(self, name):
        for loc in [self.RIGHT,
                    self.BOTTOM_RIGHT,
                    self.BOTTOM,
                    self.BOTTOM_LEFT,
                    self.LEFT,
                    self.TOP_LEFT,
                    self.TOP,
                    self.TOP_RIGHT]:
            if not self.is_conflict(loc):
                self.add(name, loc)
                return

        if self._current_column == self.column - 1:
            self._current_row += 1
            self._current_column = 0
        else:
            self._current_column += 1
        self._log.info("All slots occupied, going outside")
        self.safely_add(name)


class Node:
    def __init__(self, name):
        self.name = name
        self._inputs = []
        self._outputs = []
        self.row = None
        self.column = None
        self.slots = [None, None, None, None]

    def add_input(self, edge: Edge):
        self._inputs.append(edge)

    def add_output(self, edge: Edge):
        self._outputs.append(edge)

    @property
    def inputs(self):
        return self._inputs

    @property
    def outputs(self):
        return self._outputs

    @property
    def max_links(self):
        t1 = len(self.outputs)
        t2 = len(self.inputs)
        return t1 if t1 > t2 else t1

    def __str__(self):
        return self.name


class Network:
    def __init__(self, data, log: Log):
        self.data = data
        self._nodes = None
        self._log = log
        self._start_node = None
        self._slots = None
        self.max_rows = 5

    @property
    def nodes(self) -> dict:
        if self._nodes is None:
            self._assign_nodes()
        return self._nodes

    @property
    def slots(self) -> Slots:
        if self._slots is None:
            self._slots = Slots(self.start_node, self._log)
        return self._slots

    @property
    def start_node(self):
        if self._start_node is None:
            self._assign_nodes()
        return self._start_node

    def _assign_nodes(self):
        all_nodes = []
        for d in self.data:
            all_nodes.extend(d[:2])

        all_nodes = list(set(all_nodes))
        all_nodes = {x: Node(x) for x in all_nodes}
        self._nodes = all_nodes

        for n in self.data:
            e = Edge(n[0], n[1], n[2])
            self.nodes[e.start].add_output(e)
            self.nodes[e.end].add_input(e)

        if self._start_node is None:
            temp = [x for x in self.nodes.values()]
            temp = sorted(temp, key=lambda x: x.max_links, reverse=True)
            self._start_node = temp[0].name

    def add_slots(self, node: Node):
        if self.slots.index(node.name) is None:
            self.slots.safely_add(node.name)
        else:
            self.slots.reset_pointer(node.name)

        for out in node.outputs:
            if out.start not in self.slots.all:
                self.slots.safely_add(out.start)
                self.slots.reset_pointer(node.name)
            if out.end not in self.slots.all:
                self.slots.safely_add(out.end)
                self.slots.reset_pointer(node.name)

    def _arrange_slots(self):
        self.add_slots(self.nodes[self.start_node])
        for n in self.nodes.values():
            print(self.slots._current_column)
            self.add_slots(n)

        print(self.slots.data)

        for i, s in enumerate(self.slots.all):
            row = self.slots.get_row(i)
            col = self.slots.get_column(i)
            name = self.slots.data[row, col]
            if name is not None:
                self.slots.data[row, col] = (name, 1)

    def test(self):
        self._arrange_slots()
        print(self.slots.data)


def run():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["x", "b", 1]
    ]
    Network(data, Log()).test()

    # s = Slots("a", Log())
    # s.add("ee", s.BOTTOM_LEFT)
    # print(s.data)
    # print(s.is_conflict(s.TOP_LEFT))
