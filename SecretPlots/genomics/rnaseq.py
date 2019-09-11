# SecretPlots 2019
# Author : Rohit Suratekar
# Date : 3 September 2019
#
# All Classes and functions related to RNA-seq analysis

import matplotlib.pylab as plt
import pandas as pd
from SecretColors import Palette

from SecretPlots.constants.system import *
from SecretPlots.utils import log


class BaseAnalysis:
    def __init__(self, generate_log: bool = False,
                 logging_options: dict = None):
        self.generate_log = generate_log
        self.logging_options = logging_options
        self.palette = Palette()
        self.p = self.palette

    def analysis_name(self):
        raise NotImplementedError()

    def version_error(self):
        raise NotImplementedError()


class StringTie(BaseAnalysis):
    """
    Simple class for StringTie 2.0
    """

    # StringTie Columns

    COL_GENE_ID = "Gene ID"
    COL_GENE_NAME = "Gene Name"
    COL_REFERENCE = "Reference"
    COL_STRAND = "Strand"
    COL_START = "Start"
    COL_END = "End"
    COL_COVERAGE = "Coverage"
    COL_FPKM = "FPKM"
    COL_TPM = "TPM"

    def __init__(self, filename: str,
                 skip_header: bool = False,
                 generate_log: bool = False,
                 logging_options: dict = None):
        super().__init__(generate_log, logging_options)
        self.log("StringTie Object initiated", LOG_INFO)
        self.filename = filename
        self.skip_header = skip_header
        self.data = self.__parse_file()

    def version_error(self):
        raise Exception("This object accepts file generated by StringTie  "
                        "v2.0 ("
                        "http://ccb.jhu.edu/software/stringtie/index.shtml)."
                        " Please check the file format of this version.")

    def analysis_name(self):
        return "StringTie"

    def __parse_file(self):
        self.log("Attempting to parse {}".format(self.filename), LOG_INFO)
        with open(self.filename) as f:
            loc = f.tell()
            header = f.readline().split("\t")
            if len(header) != 9:
                self.log("Provided file is not in standard format", LOG_ERROR)
                raise self.version_error()
            if not self.skip_header:
                self.log("Header Skipped", LOG_INFO)
                f.seek(loc)

            return pd.read_csv(f, delimiter="\t")

    def log(self, message: str, log_type: int):
        if self.generate_log:
            if self.logging_options is None:
                log(message)
            else:
                self.logging_options["message"] = message
                log(**self.logging_options)

    @property
    def gene_ids(self):
        return self.data[StringTie.COL_GENE_ID].values

    @property
    def gene_names(self):
        return self.data[StringTie.COL_GENE_NAME].values

    @property
    def strands(self):
        return self.data[StringTie.COL_STRAND].values

    @property
    def locations(self):
        return self.data.apply(lambda x: (x[StringTie.COL_START],
                                          x[StringTie.COL_END]), axis=1).values

    @property
    def tpms(self):
        return self.data[StringTie.COL_TPM].values

    @property
    def fpkms(self):
        return self.data[StringTie.COL_FPKM].values

    @property
    def coverages(self):
        return self.data[StringTie.COL_COVERAGE].values

    @property
    def references(self):
        return self.data[StringTie.COL_REFERENCE].values

    @property
    def starts(self):
        return self.data[StringTie.COL_START].values

    @property
    def ends(self):
        return self.data[StringTie.COL_END].values

    @staticmethod
    def show():
        plt.show()

    def plot_tpms(self, min_value: float = 0, max_value: float = None):

        plt.hist(self.tpms)


def rr():
    s = StringTie('local/data.tsv')
    s.plot_tpms()
    s.show()


def run():
    rr()
