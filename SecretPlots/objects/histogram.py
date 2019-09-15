# SecretPlots 2019
# Author : Rohit Suratekar
# Date : 5 September 2019
#
# Histogram Object

import matplotlib.pylab as plt
import numpy as np
from SecretColors import Palette


class Histogram:
    def __init__(self):
        self.palette = Palette()
        self._c = plt

    def basic(self, data):
        self._c.hist(data)
        self._c.ylabel("Frequency")





def run():
    d = np.random.uniform(1, 100, 10)
    e = np.random.uniform(40, 80, 10)
    bb = BoxPlot([[d, e, None], [e, e, d]])
    bb.plot()
    bb.show()
