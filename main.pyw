#!/usr/bin/env python
from RouteData import RouteData
from RouteReader import RouteReader
from UI import UserInterface
from LogReader import LogReader

import logging
import logging.config
import yaml

try:
    with open('logging.yaml', 'r') as f:
        log_cfg = yaml.safe_load(f.read())
    logging.config.dictConfig(log_cfg)
    logging.info("Using customized logging defined in logging.yaml")
except FileNotFoundError:
    logging.basicConfig(filename="routeTracker.log", format="%(asctime)s - %(name)-10s - %(levelname)-5s - %(message)s",
                        level='INFO')
    logging.info("Using default logging.")


# noinspection PyBroadException
def main():
    try:
        my_ui = UserInterface()
        my_ui.main_loop()
    except Exception:
        logging.exception("Unhandled error occurred!")


if __name__ == '__main__':
    logging.getLogger('root')
    logging.debug('Starting up!')
    main()
