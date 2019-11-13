#  SecretPlots
#  Copyright (c) 2019.  SecretBiology
#
#  Author: Rohit Suratekar
#  Organisation: SecretBiology
#  Website: https://github.com/secretBiology/SecretPlots
#  Licence: MIT License
#  Creation: 11/12/19, 4:27 PM
#
# Network Location Manager

from SecretPlots.managers.location._base import LocationManager
from SecretPlots.objects import Data
from SecretPlots.constants.graph import PLOT_NETWORK


class NetworkLocation(LocationManager):

    @property
    def plot_type(self):
        return PLOT_NETWORK

    def validate(self, data: Data):
        self._log.info("Valid data is provided for the NetworkPlot")
        return True

    def get(self, data: Data):
        return None
