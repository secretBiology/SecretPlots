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
from SecretPlots.network.pathfinder import PathFinder, Space
import numpy as np
from SecretPlots.constants.network import *
import pytest


def get_data():
    data = [[0, 0, 0, 0],
            [0, None, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]]
    return data


def test_pathfinder():
    p = PathFinder(get_data())


def test_space():
    data = [
        ["a", "b", 1],
        ["a", "c", 1],
        ["a", "d", 1],
        ["b", "c", 1],
    ]

    s = Space(data)

    # Check node placement
    assert s.max_cols == 2
    assert len(s.nodes) == 4
    with pytest.raises(ValueError):
        s.max_cols = 1.5
