""" Shared utilities for DockCI log server consumer, and API """
import logging
import signal
import sys

from functools import wraps


TERM_SIGNALS = (signal.SIGINT, signal.SIGTERM)
LOG_FORMAT = ('%(levelname) -7s %(asctime)s %(name) -10s %(funcName) '
              '-10s %(lineno) -4d: %(message)s')

def run_wrapper(name):
    """ Wrap the run method to setup signals, and inject logger """
    stop_handlers = []

    def outer(func):
        @wraps(func)
        def inner():
            logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
            logger = logging.getLogger(name)

            def handle_signal(*_):
                logger.info("Shutting down")
                for handler in stop_handlers:
                    handler()
                sys.exit(0)

            for signum in TERM_SIGNALS:
                signal.signal(signum, handle_signal)

            logger.info("Running")
            try:
                return func(logger, stop_handlers.append)
            except KeyboardInterrupt:
                handle_signal()

        return inner
    return outer
