# SecretPlots 2019
# Author : Rohit Suratekar
# Date : 4 September 2019
#
# Simple utils to use in the library


def log(message: str,
        raise_error: bool = False,
        options: dict = None,
        add_to_console: bool = True,
        add_to_file: bool = False,
        filename: str = "script.log",
        logging_format: str = "%(asctime)s %(filename)s : %(message)s"):
    """Logging function

    Simple Logging function to log various activities in the code

    :param message: Message of the log
    :param raise_error: If True, it will raise Exception after logging
    :param options: Dictionary of options (if any)
    :param add_to_console: If True, log will be displayed on the console
    :param add_to_file: If True, log will be added to log file
    :param filename: Full name and path of the log file
    :param logging_format: Formatting style of the log. Please keep '%(
    message)s' term in the format to display message.
    """
    import logging
    log_object = logging.getLogger('log')
    log_object.setLevel(logging.INFO)
    formatter = logging.Formatter(logging_format)

    if add_to_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        log_object.addHandler(console)

    if add_to_file:
        log_file = logging.FileHandler(filename)
        log_file.setFormatter(formatter)
        log_object.addHandler(log_file)

    log_object.info(message)
    if raise_error:
        raise Exception(message)


def run():
    log("something else here")
