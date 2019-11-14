#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/14/19, 11:59 AM
#
#
#
from typing import List, Dict

import numpy as np

from SecretPlots.utils import Log


class Edge:
    def __init__(self, data):
        self.start = data[0]  # type:str
        self.end = data[1]  # type: str
        self.type = data[2]  # type: int


class Node:
    def __init__(self, name):
        self.name = name  # type: str
        self._inputs = []
        self._outputs = []

    @property
    def inputs(self) -> List:
        return self._inputs

    @property
    def outputs(self) -> List:
        return self._outputs

    @outputs.setter
    def outputs(self, value: List[Edge]):
        self._outputs = value

    @inputs.setter
    def inputs(self, value: List[Edge]):
        self._inputs = value

    @property
    def max_links(self) -> int:
        t1 = len(self.inputs)
        t2 = len(self.outputs)
        return t1 if t1 > t2 else t2

    def add_input(self, value):
        self._inputs.append(value)

    def add_output(self, value):
        self._outputs.append(value)

    def __repr__(self):
        return f"Node({self.name})"


class Links:
    def __init__(self):
        self.input = 0
        self.output = 0
        self.vertical = []
        self.horizontal = []

    @property
    def lines(self):
        return len(self.vertical) + len(self.horizontal)

    @property
    def is_empty(self):
        return (self.input + self.output + self.lines) == 0

    def __repr__(self):
        return f"({self.output},{self.lines},{self.input})"

    def add_vertical(self, node, line_type):
        self.vertical.append((node, line_type))

    def add_horizontal(self, node, line_type):
        k = (node, line_type)
        if k not in self.horizontal:
            self.horizontal.append(k)


class Item:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        if type(self.value) == str:
            return f"(  \033[91m{str(self.value)}\033[0m  )"
        else:
            if self.value.is_empty:
                return "(     )"

            return str(self.value)

    def add_input(self, links: int):
        self.value.input = links

    def add_output(self, links: int):
        self.value.output = links

    @property
    def is_node(self):
        return type(self.value) == str


class Space:
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"

    # In default order or preference
    LOCATIONS = {
        BOTTOM_RIGHT: (2, 2),
        BOTTOM: (2, 0),
        BOTTOM_LEFT: (2, -2),
        LEFT: (0, -2),
        TOP_LEFT: (-2, -2),
        TOP: (-2, 0),
        TOP_RIGHT: (-2, 2),
        RIGHT: (0, 2)
    }

    DIRECTION = [RIGHT, BOTTOM, LEFT, TOP]

    def __init__(self, start_node: Node, log: Log):
        self.data = np.asanyarray([Item(start_node.name)]).reshape(1, 1)
        self.total_rows = 1
        self.total_cols = 1
        self._all_nodes = []

        # Initial setup for the start_node
        self._add_column(True)
        self._add_column(False)
        self._add_row(True)
        self._add_row(False)
        input_link = Links()
        input_link.input = len(start_node.inputs)
        out_link = Links()
        out_link.output = len(start_node.outputs)
        for out in start_node.outputs:
            out_link.add_horizontal(start_node.name, out.type)
        self.data[0, 1] = Item(input_link)
        self.data[2, 1] = Item(out_link)

        self._all_nodes.append(start_node.name)

        self._log = log
        self._log.info(
            f"Empty space is initialized with starting node {start_node.name}")

    @property
    def all_nodes(self) -> list:
        return self._all_nodes

    def coord(self, element: str) -> tuple:
        ind = list([x.value for x in self.data.flatten()]).index(element)
        return ind, int(ind / self.total_cols), ind % self.total_cols

    def _reset_stats(self):
        self.total_rows = self.data.shape[0]
        try:
            self.total_cols = self.data.shape[1]
        except IndexError:
            self.total_cols = 1

    def _add_row(self, on_top: bool):
        f = np.array([Item(Links()) for _ in range(self.total_cols)])
        if on_top:
            self.data = np.vstack((f, self.data))
        else:
            self.data = np.vstack((self.data, f))
        self._reset_stats()

    def _add_column(self, on_right: bool):
        f = (np.asanyarray([Item(Links()) for _ in range(self.total_rows)])
             .reshape(self.total_rows, 1))
        if on_right:
            self.data = np.hstack((self.data, f))
        else:
            self.data = np.hstack((f, self.data))
        self._reset_stats()

    def _put_on_location(self, start_node, name, location):
        _, row, col = self.coord(start_node)
        row_factor, column_factor = self.LOCATIONS[location]
        row += row_factor
        col += column_factor
        if row >= self.total_rows:
            self._add_row(False)
            self._add_row(False)
        if row < 0:
            self._add_row(True)
            self._add_row(True)
            row = 1
        if col >= self.total_cols:
            self._add_column(True)
            self._add_column(True)
        if col < 0:
            self._add_column(False)
            self._add_column(False)
            col = 1
        self.data[row, col] = Item(name)

    def _add_directions(self, node: Node):
        _, row, col = self.coord(node.name)
        self.data[row - 1, col].add_input(len(node.inputs))
        self.data[row + 1, col].add_output(len(node.outputs))
        for out in node.outputs:
            self.data[row + 1, col].value.add_horizontal(node.name, out.type)

    def _get_item_at(self, name, loc):
        _, row, col = self.coord(name)
        f_row, f_col = self.LOCATIONS[loc]
        row += f_row
        col += f_col
        if row <= 0 or col <= 0:
            return None
        if row >= self.total_rows or col >= self.total_cols:
            return None
        return self.data[row, col]

    def _add_lines(self, node: Node):
        for loc in self.LOCATIONS:
            m = self._get_item_at(node.name, loc)
            if m is not None:
                print(m, loc)

    def add(self, start_node: str, node: Node):
        if node.name in self.all_nodes:
            self._log.warn(f"Addition of {node.name} is skipped as it is "
                           f"already present in the space")
            return

        for loc in self.LOCATIONS:
            itm = self._get_item_at(start_node, loc)
            if itm is None or type(itm.value) != str:
                self._put_on_location(start_node, node.name, loc)
                self._add_directions(node)
                self._all_nodes.append(node.name)
                self._log.info(f"New node {node.name} is added to the space.")
                return

        self._log.info(f"No space around {start_node} found. Searching "
                       f"around other random nodes.")
        for n in self.all_nodes:
            if n != start_node:
                self.add(n, node)

    def get_item(self, row, col, loc):
        if loc == self.TOP:
            if row == 0:
                return None
            return self.data[row - 1, col]
        elif loc == self.LEFT:
            if col == 0:
                return None
            return self.data[row, col - 1]
        elif loc == self.BOTTOM:
            if row == self.total_rows - 1:
                return None
            return self.data[row + 1, col]
        elif loc == self.RIGHT:
            if col == self.total_cols - 1:
                return None
            return self.data[row, col + 1]
        else:
            self._log.error(f"Unknown direction '{loc}' for connection", True)

    def _availability(self, row, col, name):

        def _nn(val):
            if val is None:
                return 0
            if val.is_node:
                if val.value == name:
                    return 2
                else:
                    return 0
            else:
                return 1

        return [_nn(self.get_item(row, col, x)) for x in self.DIRECTION]

    def _connect_next(self, row, col, line_type, name):
        av = self._availability(row, col, name)
        if 2 in av:
            return
        else:
            for loc, val in zip(self.DIRECTION, av):
                if val == 1:
                    k = (name, line_type)
                    item = self.get_item(row, col, loc)
                    lk = item.value  # type: Links
                    if loc in [self.TOP, self.BOTTOM]:
                        if k in lk.vertical:
                            return
                        else:
                            lk.add_vertical(name, line_type)
                    else:
                        if k in lk.horizontal:
                            return
                        else:
                            lk.add_horizontal(name, line_type)

                    print(self.data)
                    print("")
                    print("")
                    print("")
                    print("")
                    if loc == self.TOP:
                        self._connect_next(row - 1, col, line_type, name)
                    elif loc == self.BOTTOM:
                        self._connect_next(row + 1, col, line_type, name)
                    elif loc == self.LEFT:
                        self._connect_next(row, col - 1, line_type, name)
                    else:
                        self._connect_next(row, col + 1, line_type, name)

    def connect(self, start, end, line_type):
        _, start_row, start_col = self.coord(start)
        self._connect_next(start_row + 1, start_col, line_type, end)

    def pretty(self):
        d = self.data[1::2, 1::2]
        print(d)


class Network:
    def __init__(self, data, log: Log):
        self.data = data
        self._log = log
        self._nodes = None
        self._start_node = None
        self._space = None

        self._log.info("Empty network is initialized.")

    @property
    def start_node(self) -> str:
        if self._start_node is None:
            self._assign_nodes()
        return self._start_node

    @property
    def space(self) -> Space:
        if self._space is None:
            self._generate_space()
        return self._space

    @property
    def nodes(self) -> Dict[str, Node]:
        if self._nodes is None:
            self._assign_nodes()
        return self._nodes

    def _assign_nodes(self):
        all_nodes = []
        for d in self.data:
            all_nodes.extend(d[:2])
        all_nodes = sorted(list(set(all_nodes)))
        all_nodes = {x: Node(x) for x in all_nodes}
        self._nodes = all_nodes
        self._assign_edges()
        self._log.info("Nodes are arranged")

    def _assign_edges(self):

        def _get(value):
            return self.nodes[value].max_links

        # Simply add all the interactions to each node
        for n in self.data:
            e = Edge(n)
            self.nodes[e.start].add_output(e)
            self.nodes[e.end].add_input(e)

        # Sort the links based on their start points
        for n in self.nodes.values():
            all_outputs = n.outputs
            all_outputs = [(_get(x.end), x) for x in all_outputs]
            all_outputs = sorted(all_outputs,
                                 key=lambda x: x[0],
                                 reverse=False)
            all_outputs = [x[1] for x in all_outputs]
            n.outputs = all_outputs

        # Create start node
        if self._start_node is None:
            temp = [(x.name, x.max_links) for x in self.nodes.values()]
            temp = sorted(temp, key=lambda x: x[1], reverse=True)
            self._start_node = temp[0][0]

        self._log.info("Edges are added to nodes")

    def _add_connections(self):
        for d in self.data:
            self.space.connect(d[0], d[1], d[2])
            break

    def _generate_space(self):
        self._space = Space(self.nodes[self.start_node], self._log)
        sn = self.start_node
        for n in self.nodes.values():
            self.space.add(sn, n)
            for out in n.outputs:
                self.space.add(sn, self.nodes[out.end])
            sn = n.name

    def test(self):
        self._generate_space()
        self._add_connections()
        print(self.space.data)


def run():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["b", "c", 1],
    ]
    Network(data, Log()).test()
