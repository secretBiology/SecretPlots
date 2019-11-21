#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/15/19, 11:09 AM
#
#
# Path finder functions related to the our network

from typing import List, Dict, Union

import numpy as np


# np.set_printoptions(linewidth=300)


class Point:
    def __init__(self, index: int):
        self.index = index
        self.row = None
        self.column = None
        self.mark = "."
        self.value = np.inf
        self.original_value = None
        self.previous_node = None

    @property
    def pos(self):
        return self.row, self.column

    def __repr__(self):
        return f"{self.mark}"
        # return f"({self.value}, {self.previous_node})"

    def update(self, value, node):
        if value < self.value:
            self.value = value
            self.previous_node = node


class PathFinder:
    def __init__(self, graph):
        self._raw_data = np.asanyarray(graph)
        self._graph = None
        self.path_mark = "o"
        self.empty_mark = "."
        self.block_mark = "|"
        self.end_mark = "X"
        self.start_mark = "o"
        self.block_item = None
        self.block_penalty = np.inf
        self.show_blocks = False

    @property
    def graph(self) -> np.ndarray:
        if self._graph is None:
            self._generate_nodes()
        return self._graph

    @property
    def columns(self):
        return self.graph.shape[1]

    @property
    def rows(self):
        return self.graph.shape[0]

    def _generate_nodes(self):
        data = self._raw_data.flatten()
        new_data = []
        for i in range(len(data)):
            node = Point(i)
            node.row = int(i / self._raw_data.shape[1])
            node.column = i % self._raw_data.shape[1]
            node.original_value = data[i]
            node.mark = self.empty_mark
            if self.show_blocks and node.original_value == self.block_item:
                node.mark = self.block_mark
            new_data.append(node)

        data = new_data
        data = np.array(data, dtype=Point).reshape(self._raw_data.shape)
        self._graph = data

    def get_surrounding(self, row, col) -> List[Point]:
        def _get_item(r, c):
            if r < 0 or c < 0 or r >= self.rows or c >= self.columns:
                return None
            else:
                return self.graph[r, c]

        data = [
            _get_item(row, col + 1),  # Right
            _get_item(row + 1, col),  # Bottom
            _get_item(row, col - 1),  # Left
            _get_item(row - 1, col)  # Top

        ]
        return [x for x in data if x is not None]

    def dijkstra_distance(self, start_node: Point, end_node: Point):
        if end_node.original_value == self.block_item:
            return self.block_penalty
        return start_node.value + 1

    @staticmethod
    def cartesian_distance(node1: Point, node2: Point):
        y1, x1 = node1.pos
        y2, x2 = node2.pos
        return np.sqrt(np.square(x1 - x2) + np.square(y1 - y2))

    def a_star_distance(self,
                        start_node: Point,
                        end_node: Point,
                        final_node: Point):

        if end_node.original_value == self.block_item:
            return self.block_penalty
        return start_node.value + self.cartesian_distance(end_node, final_node)

    def _generate_distance_matrix(self,
                                  start_index: int,
                                  end_index: int, *,
                                  use_dijkstra: bool):

        start_row, start_col = self.split_index(start_index, self.columns)
        end_row, end_col = self.split_index(end_index, self.columns)
        self.graph[start_row, start_col].value = 0
        unvisited = [x for x in self.graph.flatten()]
        while len(unvisited) >= 1:
            unvisited = sorted(unvisited, key=lambda x: x.value)
            current = unvisited[0]
            row, col = current.pos
            for a in self.get_surrounding(row, col):
                if use_dijkstra:
                    a.update(self.dijkstra_distance(current, a), current.index)
                else:
                    a.update(
                        self.a_star_distance(current,
                                             a,
                                             self.graph[end_row, end_col]),
                        current.index)
            unvisited.remove(current)

    @staticmethod
    def split_index(index, width):
        row = int(index / width)
        col = index % width
        return row, col

    def _trace_path(self, start, end) -> list:
        path = []
        row, col = self.split_index(end, self.columns)
        item = self.graph[row, col]  # type:Point
        path.append(item.index)
        while item != start:

            item.mark = self.path_mark
            if item.index == end:
                item.mark = self.end_mark
            elif item.index == start:
                item.mark = self.start_mark
            if item.previous_node is None:
                break
            nr, nc = self.split_index(item.previous_node, self.columns)
            item = self.graph[nr, nc]
            path.append(item.index)

        path = list(reversed(path))
        return path

    def find_path(self, start, end, *, use_dijkstra=False):
        self._generate_distance_matrix(start, end, use_dijkstra=use_dijkstra)
        self._trace_path(start, end)
        print(self.graph)
        # Reset Data
        self._generate_nodes()

    def boolean_path(self, start, end, *,
                     use_dijkstra=False,
                     exclude_start=False,
                     exclude_end=False) -> np.ndarray:

        self._generate_distance_matrix(start, end, use_dijkstra=use_dijkstra)
        self._trace_path(start, end)
        data = self.graph.flatten()
        for i in range(len(data)):
            if data[i].mark in [self.path_mark, self.end_mark]:
                data[i] = 1
            else:
                data[i] = 0
        if exclude_start:
            data[start] = 0
        if exclude_end:
            data[end] = 0
        data = np.asanyarray(data).reshape(self.graph.shape)
        return data

    def path_index(self, start, end, *,
                   use_dijkstra=False,
                   exclude_start=False,
                   exclude_end=False) -> list:

        self._generate_distance_matrix(start, end, use_dijkstra=use_dijkstra)
        return self._trace_path(start, end)


class MatItem:

    def __init__(self, height, width):
        self.x = None
        self.y = None
        self.height = height
        self.width = width
        self.name = "N/A"
        self.column = None
        self.row = None

    def assign(self, index: int, width: int):
        row = int(index / width)
        col = index % width
        self.x = col * self.width
        self.y = row * self.height
        self.column = col
        self.row = row

    @property
    def is_gap(self):
        raise NotImplementedError()


class Edge:
    def __init__(self, start, end, link_type):
        self.start = start
        self.end = end


class Node(MatItem):
    @property
    def is_gap(self):
        return False

    def __init__(self, name, height, width):
        super().__init__(height, width)
        self.name = name
        self.links = 0
        self.paths = {}
        self.color = None

    def __repr__(self):
        return f"({self.name} {self.links})"

    def add_paths(self, node_name, indexes):
        self.paths[node_name] = indexes


class Gap(MatItem):
    @property
    def is_gap(self):
        return True

    def __init__(self, height, width):
        super().__init__(height, width)
        self.lines = []
        self.v_slots = 1
        self.h_slots = 1

    def add_line(self, node_name: str):
        if node_name not in self.lines:
            self.lines.append(node_name)

    def __repr__(self):
        if len(self.lines) == 0:
            return f"(   )"
        else:
            return f"( {''.join(self.lines)} )"


class Space:
    def __init__(self, data, height, width):
        self._raw_data = data
        self._nodes = None
        self._max_cols = None
        self._matrix = None
        self.node_gap = 1
        self.use_dijkstra = True
        self.node_height = height
        self.node_width = width
        self._assignment_done = False

    @property
    def nodes(self) -> Dict[str, Node]:
        if self._nodes is None:
            nodes = {}
            # Create empty nodes
            for d in self._raw_data:
                nodes[d[0]] = Node(d[0], height=self.node_height,
                                   width=self.node_width)
                nodes[d[1]] = Node(d[1], height=self.node_height,
                                   width=self.node_width)

            # Add details
            for d in self._raw_data:
                nodes[d[0]].links += 1
                nodes[d[1]].links += 1

            self._nodes = nodes
        return self._nodes

    @property
    def max_cols(self) -> int:
        if self._max_cols is None:
            self._max_cols = int(np.sqrt(len(self.nodes)))
        return self._max_cols

    @max_cols.setter
    def max_cols(self, value: int):
        if not isinstance(value, int):
            raise ValueError(f"Column size can not be {type(value)}")
        self._max_cols = value

    @property
    def matrix(self) -> np.ndarray:
        if self._matrix is None:
            self._place_nodes()
        return self._matrix

    def _place_nodes(self):

        mat = [x for x in self.nodes.values()]
        forward_array = []
        reverse_array = []
        swap_array = True
        while len(mat) > 0:
            mat = sorted(mat, key=lambda x: x.links, reverse=True)
            if swap_array:
                forward_array.append(mat[0])
            else:
                reverse_array.append(mat[0])
            mat.pop(0)
            swap_array = not swap_array
        mat = forward_array
        mat.extend(reversed(reverse_array))

        while len(mat) % self.max_cols != 0:
            mat.insert(-1, None)

        mat = np.array(mat).reshape((-1, self.max_cols))

        self._matrix = mat

    def _add_space(self):
        ng = self.node_gap + 1
        rows = self.matrix.shape[0] * ng + (ng - 1)
        cols = self.matrix.shape[1] * ng + (ng - 1)
        a = [None] * rows * cols
        a = np.array(a).reshape((rows, cols))
        a[(ng - 1)::ng, (ng - 1)::ng] = self.matrix
        k = [Gap(height=self.node_height,
                 width=self.node_width) if x is None else x
             for x in a.flatten()]
        k = np.array(k).reshape(a.shape)
        self._matrix = k

    @property
    def boolean_matrix(self) -> np.ndarray:
        x = [0 if m.is_gap else None for m in self.matrix.flatten()]
        x = np.array(x).reshape(self.matrix.shape)
        return x

    def _get_node_coord(self, node: Node) -> tuple:
        k = list(self.matrix.flatten())
        k = k.index(node)
        return self._convert_idx(k)

    def _get_node_index(self, node: Node, is_output: bool):
        row, col = self._get_node_coord(node)
        if is_output:
            row -= 1  # TODO: Check properly
        else:
            row += 1
        return row * self.matrix.shape[1] + col

    def _get_item_at(self, index: int) -> Union[Gap, Node]:
        row, col = self._convert_idx(index)
        return self.matrix[row, col]

    def _convert_idx(self, idx) -> tuple:
        row = int(idx / self.matrix.shape[1])
        col = idx % self.matrix.shape[1]
        return row, col

    def _assign_edges(self):
        for d in self._raw_data:
            p = PathFinder(self.boolean_matrix)
            start_node = self._get_node_index(self.nodes[d[0]], True)
            end_node = self._get_node_index(self.nodes[d[1]], False)
            idx = []
            for i in p.path_index(start_node, end_node,
                                  use_dijkstra=self.use_dijkstra):
                r, c = self._convert_idx(i)
                idx.append((i, r, c))

            self.nodes[d[0]].add_paths(d[1], idx)

    def get(self) -> np.ndarray:
        if not self._assignment_done:
            self._add_space()
            self._assign_edges()
            self._assignment_done = True
        return self.matrix


def run():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["a", "d", 1],
        ["c", "d", 1],
        ["b", "d", 1],
    ]
