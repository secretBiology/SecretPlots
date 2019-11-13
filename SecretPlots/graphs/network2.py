#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/12/19, 2:13 PM

# Network Plot

import random
import string

from SecretPlots.utils import Log


class Node:
    def __init__(self, name):
        self.name = name
        self._inputs = []
        self._outputs = []
        self.x = None
        self.y = None
        self.slots = [None, None, None, None]

    @property
    def pos(self):
        return self.x, self.y

    def add_input(self, value):
        if value not in self._inputs:
            self._inputs.append(value)

    def add_output(self, value):
        if value not in self._outputs:
            self._outputs.append(value)

    @property
    def inputs(self):
        return self._inputs

    @property
    def outputs(self):
        return self._outputs

    @property
    def max_links(self):
        p1 = len(self.inputs)
        p2 = len(self.outputs)
        return p1 if p1 > p2 else p2

    def fill_slot(self, node_name):
        for i, s in enumerate(self.slots):
            if s is None:
                self.slots[i] = node_name
                return True
        return False

    def slot_location(self, node_name):
        if node_name in self.slots:
            return self.slots.index(node_name)
        else:
            return -1

    @staticmethod
    def _reverse_slot(number):
        if number == 0:
            return 1
        elif number == 1:
            return 0
        elif number == 2:
            return 3
        else:
            return 2

    def assign_slot(self, node_name, slot_loc):
        loc = self._reverse_slot(slot_loc)
        if self.slots[loc] is None:
            self.slots[loc] = node_name
        else:
            raise Exception("Conflicting slot location")


class Interactions:
    def __init__(self, data, log: Log):
        self._log = log
        self.data = data
        self.rows = 2
        self._nodes = None
        self.start_node = None
        self.width = 1
        self.height = 1
        self.stem = 0.2
        self.stem_increment = 0.1
        self._node_matrix = []

    @property
    def nodes(self) -> dict:
        if self._nodes is None:
            self._assign_nodes()
        return self._nodes

    def _assign_nodes(self) -> None:
        all_nodes = []
        for k in self.data:
            all_nodes.extend(k[:-1])
        all_nodes = list(set(all_nodes))
        all_nodes = {x: Node(x) for x in all_nodes}
        for k in self.data:
            all_nodes[k[1]].add_input(k)
            all_nodes[k[0]].add_output(k)

        if self.start_node is None:
            temp = []
            for k in all_nodes.values():
                temp.append((k.name, k.max_links))
            temp = sorted(temp, key=lambda x: x[1], reverse=True)
            self.start_node = temp[0][0]

        self._nodes = all_nodes

    def _generate_slot(self, node: Node):
        for out in node.outputs:
            if node.fill_slot(out[1]):
                self.nodes[out[1]].assign_slot(
                    node.name,
                    node.slot_location(out[1]))
            else:
                self._generate_slot(self.nodes[out[1]])

    def test(self, node_name):
        if node_name not in self._node_matrix:
            self._node_matrix.append(node_name)
        

    def _assign(self):
        # Set starting node to 0, 0
        self.nodes[self.start_node].x = 0
        self.nodes[self.start_node].y = 0

        self.test(self.start_node)

        # self._generate_slot(self.nodes[self.start_node])
        #
        # for a in self.nodes:
        #     print(a, self.nodes[a].slots)


def rand_interactions():
    data = []
    for j in range(10):
        data.append([random.choice(string.ascii_lowercase), random.choice(
            string.ascii_lowercase), 1])
    return data


def run():
    data = [
        ["a", "b", 1],
        ["a", "x", 1],
        ["a", "c", 1],
        ["x", "c", 1],
        ["x", "o", 1],
    ]
    i = Interactions(data, Log())
    i._assign()
