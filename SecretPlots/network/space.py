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
from typing import List, Dict, Union

import numpy as np

from SecretPlots.constants.network import *
from SecretPlots.utils import Log


class Edge:
    def __init__(self, data, **options):
        self.start = data[0]
        self.end = data[1]
        self.value = data[2]
        self.options = options

    def __repr__(self):
        return f"{self.start}->{self.end}"


class Node:
    def __init__(self, name):
        self.name = name
        self._inputs = []
        self._outputs = []

    def add_input(self, value: Edge):
        self._inputs.append(value)

    def add_output(self, value: Edge):
        self._outputs.append(value)

    @property
    def outputs(self) -> List[Edge]:
        return self._outputs

    @property
    def inputs(self) -> List[Edge]:
        return self._inputs

    @inputs.setter
    def inputs(self, values: list):
        self._inputs = values

    @outputs.setter
    def outputs(self, values: list):
        self._outputs = values

    @property
    def max_links(self) -> int:
        t1 = len(self.outputs)
        t2 = len(self.inputs)
        return t1 if t1 > t2 else t2

    def __repr__(self):
        return f"Node({self.name})"


class Gap:
    def __init__(self):
        self._lines = 0
        self.value = None

    def __repr__(self):
        return "(     )"


class Space:
    def __init__(self, start_node, log: Log):

        self._start_node = start_node
        self.data = (
            np.asanyarray(start_node).reshape(1, 1))  # type:np.ndarray
        self._log = log
        self.gap = 1
        self._initial_setup()

        self._log.info("Blank Space is initialized")

    def _initial_setup(self):
        self._add_space(RIGHT)
        self._add_space(TOP)
        self._add_space(BOTTOM)
        self._add_space(LEFT)
        self._log.info(f"Default space is generated with "
                       f"{self._start_node.name} as middle node")

    def _add_space(self, direction):
        # Row and column are swapped to fit correct dimension while stacking
        row = self.data.shape[1]
        col = self.data.shape[0]
        row = np.asanyarray([Gap() for _ in range(row)]).reshape(1, row)
        col = np.asanyarray([Gap() for _ in range(col)]).reshape(col, 1)

        if direction == TOP:
            for _ in range(self.gap):
                self.data = np.vstack((row, self.data))
        elif direction == BOTTOM:
            for _ in range(self.gap):
                self.data = np.vstack((self.data, row))
        elif direction == LEFT:
            for _ in range(self.gap):
                self.data = np.hstack((col, self.data))
        elif direction == RIGHT:
            for _ in range(self.gap):
                self.data = np.hstack((self.data, col))
        elif direction in [TOP_LEFT, TOP_RIGHT]:
            self._add_space(TOP)
            if direction == TOP_LEFT:
                self._add_space(LEFT)
            else:
                self._add_space(RIGHT)
        elif direction in [BOTTOM_LEFT, BOTTOM_RIGHT]:
            self._add_space(BOTTOM)
            if direction == BOTTOM_LEFT:
                self._add_space(LEFT)
            else:
                self._add_space(RIGHT)
        else:
            self._log.error(f"Unknown direction {direction}")

    def get_location(self, node: Union[Node, Gap]) -> tuple:
        row, col = np.where(self.data == node)
        if len(row) == 0:
            self._log.error(f"No such node found in the Space. Please check "
                            f"if you have added '{node.name}' into the Space.")
        if len(row) > 1 or len(col) > 1:
            self._log.warn(
                f"Duplicated nodes found in the data : {node.name} ")
        return row[0], col[0]

    def _item_in_direction(self, node: Node, direction):
        def _get(r, c):
            if (r < 0
                    or c < 0
                    or r >= self.data.shape[0]
                    or c >= self.data.shape[1]):
                return None
            return self.data[r, c]

        row, col = self.get_location(node)
        factors = {
            TOP: (-self.gap - 1, 0),
            TOP_RIGHT: (-self.gap - 1, self.gap + 1),
            RIGHT: (0, self.gap + 1),
            BOTTOM_RIGHT: (self.gap + 1, self.gap + 1),
            BOTTOM: (self.gap + 1, 0),
            BOTTOM_LEFT: (self.gap + 1, -self.gap - 1),
            LEFT: (0, -self.gap - 1),
            TOP_LEFT: (-self.gap - 1, -self.gap - 1)
        }
        if direction is not None:
            fr, fc = factors[direction]
            row += fr
            col += fc
            return _get(row, col)
        else:
            all_loc = []
            for d in DIRECTIONS:
                fr, rc = factors[d]
                row += fr
                col += rc
                all_loc.append(_get(row, col))
            return all_loc

    def _check_clash(self, node: Node, direction: int = None):
        if direction is not None:
            return self._item_in_direction(node, direction)
        return 0

    def add_node(self, node: Node, direction: int, existing_node: Node = None):
        if existing_node is None:
            existing_node = self._start_node
        av = self._check_clash(existing_node, direction)  # type:Gap
        if av is not None:
            r, c = self.get_location(av)
            self.data[r, c] = node
        else:
            self._add_space(direction)
            print("here")

    def test(self):
        n = Node("c")
        self.add_node(n, BOTTOM_LEFT)
        print(self.data)


class Network:
    def __init__(self, data, log: Log):
        self.data = data
        self._log = log
        self._nodes = None
        self._starting_node = None
        self._space = None

    @property
    def nodes(self) -> Dict[str, Node]:
        if self._nodes is None:
            self._generate_nodes()
        return self._nodes

    @property
    def starting_node(self) -> Node:
        if self._starting_node is None:
            self._generate_nodes()
        return self._starting_node

    @property
    def space(self):
        if self._space is None:
            self._generate_space()
        return self._space

    def _generate_space(self):
        s = Space(self.starting_node, self._log)
        s.test()

    def _generate_nodes(self):
        all_nodes = []
        for d in self.data:
            all_nodes.extend(d[:2])
        # Sort here to get consistent results
        all_nodes = sorted(list(set(all_nodes)))
        all_nodes = {x: Node(x) for x in all_nodes}
        self._nodes = all_nodes
        self._generate_edges()

    def _generate_edges(self):
        for d in self.data:
            e = Edge(d)
            self.nodes[e.start].add_output(e)
            self.nodes[e.end].add_input(e)

        # Normalize the input and output
        for n in self.nodes.values():
            outs = n.outputs
            outs = [(x, len(self.nodes[x.end].outputs)) for x in outs]
            outs = sorted(outs, key=lambda x: x[1])
            n.outputs = [x[0] for x in outs]

            ins = n.inputs
            ins = [(x, len(self.nodes[x.end].inputs)) for x in ins]
            ins = sorted(ins, key=lambda x: x[1])
            n.inputs = [x[0] for x in ins]

        if self._starting_node is None:
            temp = [(x.name, x.max_links) for x in self.nodes.values()]
            temp = sorted(temp, key=lambda x: x[1], reverse=True)
            self._starting_node = self.nodes[temp[0][0]]

    def test(self):
        n = self.space


def run():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["b", "c", 1],
        ["x", "b", 1]
    ]

    Network(data, Log()).test()
