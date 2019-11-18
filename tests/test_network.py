#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/16/19, 10:18 PM
#
#
# Tests for network module

from SecretPlots.utils import Log
from SecretPlots.network.pathfinder import PathFinder
from SecretPlots.network.space import Space, Node
import numpy as np
from SecretPlots.constants.network import *


def get_data():
    data = [[0, 0, 0, 0],
            [0, None, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]]
    return data


def test_pathfinder():
    p = PathFinder(get_data())


def test_space():
    n = Node("a")
    s = Space(n, Log())
    # Check if data is properly formatted
    assert s.data.shape == (3, 3)
    assert isinstance(s.data, np.ndarray)
    assert s.data[1, 1] == n

    # Check if node adding function works properly
    for d in DIRECTIONS:
        s.add_node(Node(f"b{d}"), d)

    print(s.data)
