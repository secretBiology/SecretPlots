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

from typing import List

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
            if r < 0 or c < 0 or r >= self.rows or c >= self.rows:
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

    def _trace_path(self, start, end):
        row, col = self.split_index(end, self.columns)
        item = self.graph[row, col]  # type:Point
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


def run():
    data = [
        [0, None, 0, 0, 0],
        [0, 0, 0, None, 0],
        [0, 0, None, 0, 0],
        [0, 0, 0, 0, 0]
    ]

    pf = PathFinder(data)
    pf.find_path(2, 10)
    data = pf.boolean_path(2, 10)
    print(data)
