import logging

# this stores all the loggers and handlers
fiddy_loggers: dict = {}


def logger(name: str = __name__,
           log_file: str = '/tmp/fiddy.log',
           verbose: int = 3) -> logging.Logger:
    ''' Setting up logging

    Parameters
    ----------
    verbose: int, defaults = 3
        > 3 = DEBUG
          2 = INFO
          1 = WARNING
          0 = ERROR
    '''

    # need to make modifcation to this dict
    global fiddy_loggers

    # logformatter
    log_format = logging.Formatter("%(asctime)s %(funcName)s "
                                   "[%(levelname)s] %(message)s")

    # correlating log level to actual log levels
    log_levels: dict = {
        3: 10,
        2: 20,
        1: 30,
        0: 40
    }
    if verbose > 3:
        verbose = 3
    elif verbose < 0:
        verbose = 0

    # If logger already exist
    if fiddy_loggers.get(name):
        return fiddy_loggers.get(name)

    # set logging
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    # set filehandler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_format)
    file_handler.setLevel(log_levels[verbose])
    log.addHandler(file_handler)

    # set console logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(log_levels[verbose])
    log.addHandler(console_handler)

    # add it into the global logging
    fiddy_loggers[name]: logging.Logger = log

    return log
