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

np.set_printoptions(linewidth=300)


class Node:
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
        if self.original_value is None:
            return f"|"
        return f"{self.mark}"
        # return f"({self.value}, {self.previous_node})"

    def update(self, value, node):
        if value < self.value:
            self.value = value
            self.previous_node = node


def generate_nodes(graph: np.ndarray):
    data = graph.flatten()
    new_data = []
    for i in range(len(data)):
        node = Node(i)
        node.row = int(i / graph.shape[1])
        node.column = i % graph.shape[1]
        node.original_value = data[i]
        new_data.append(node)

    data = new_data
    data = np.array(data, dtype=Node).reshape(graph.shape)
    return data


def get_surrounding(graph, row, col) -> List[Node]:
    def _get_item(r, c):
        if r < 0 or c < 0 or r >= graph.shape[0] or c >= graph.shape[1]:
            return None
        else:
            return graph[r, c]

    data = [
        _get_item(row, col + 1),  # Right
        _get_item(row + 1, col),  # Bottom
        _get_item(row, col - 1),  # Left
        _get_item(row - 1, col)  # Top

    ]
    return [x for x in data if x is not None]


def dijkstra_distance(start_node: Node, end_node):
    if end_node.original_value is None:
        return np.inf
    return start_node.value + 1


def cartesian_distance(node1: Node, node2: Node):
    y1, x1 = node1.pos
    y2, x2 = node2.pos
    return np.sqrt(np.square(x1 - x2) + np.square(y1 - y2))


def a_star_distance(start_node: Node, end_node: Node, final_node: Node):
    if end_node.original_value is None:
        return np.inf
    return start_node.value + cartesian_distance(end_node, final_node)


def distance_matrix(graph: np.ndarray, start_index: int, end_index: int, *,
                    use_a_star: bool = False):
    start_row, start_col = split_index(start_index, graph.shape[1])
    end_row, end_col = split_index(end_index, graph.shape[1])
    graph[start_row, start_col].value = 0
    unvisited = [x for x in graph.flatten()]
    while len(unvisited) >= 1:
        unvisited = sorted(unvisited, key=lambda x: x.value)
        current = unvisited[0]
        row, col = current.pos
        for a in get_surrounding(graph, row, col):
            if not use_a_star:
                a.update(dijkstra_distance(current, a), current.index)
            else:
                a.update(
                    a_star_distance(current, a, graph[end_row, end_col]),
                    current.index)
        unvisited.remove(current)
    return graph


def split_index(index, width):
    row = int(index / width)
    col = index % width
    return row, col


def trace_path(graph: np.ndarray, start, end):
    row, col = split_index(end, graph.shape[1])
    item = graph[row, col]  # type:Node
    while item != start:
        item.mark = "o"
        if item.index == end:
            item.mark = "X"
        if item.previous_node is None:
            break
        nr, nc = split_index(item.previous_node, graph.shape[1])
        item = graph[nr, nc]

    print(graph)


def find_path(graph: np.ndarray, start, end):
    f = distance_matrix(graph, start, end, use_a_star=True)
    trace_path(f, start, end)


def run():
    data = [
        [0, 0, 0, 0, 0],
        [0, 0, None, 0, 0],
        [0, 0, 0, 0, 0],
        [0, None, 0, 0, 0]
    ]

    data = np.asanyarray(data)
    data = generate_nodes(data)
    find_path(data, 0, 17)
