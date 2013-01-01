#!/usr/bin/env python

import logging
import signal
import time
from threading import Thread, Event

from lib.logger import configure_logging
from lib.util import parse_options
from lib.util import read_config
from lib.config import Config
from resources.clouds import Clouds
from resources.master import Master
from resources.workers import Workers
from resources.workload import Workload
from resources.monitor import Monitor
from resources.failuresimulator import FailureSimulator

SIGEXIT = False
LOG = logging.getLogger(__name__)


class Downscaling(Thread):
    def __init__(self, config):

        Thread.__init__(self)
        self.config = config

    def run(self):
        LOG.info("Starting Downscaling")
        #TODO(dmdu): do something

        self.clouds = Clouds(self.config)

        self.clouds.selected_terminate()


        self.master = Master(self.config, self.clouds)
        self.workers = Workers(self.config, self.clouds, self.master)
        self.workload = Workload(self.config, self.master)
        self.workload.execute()

        self.monitor = Monitor(self.config, self.master)
        self.monitor.start()
        self.failuresimulator_stop= Event()
        self.failuresimulator = FailureSimulator(self.failuresimulator_stop, self.config, self.workers)
        self.failuresimulator.start()

        while self.monitor.isAlive():
            time.sleep(5)

        if self.failuresimulator.isAlive():
            self.failuresimulator_stop.set()

        self.clouds.selected_terminate()

def clean_exit(signum, frame):
    global SIGEXIT
    SIGEXIT = True
    LOG.critical("Exit signal received. Exiting at the next sane time. "
                 "Please stand by.")

def main():
    (options, args) = parse_options()
    configure_logging(options.debug)

    config = Config(options)

    signal.signal(signal.SIGINT, clean_exit)
    downscaling = Downscaling(config)
    downscaling.start()

    # wake every seconed to make sure signals are handled by the main thread
    # need this due to a quirk in the way Python threading handles signals
    while downscaling.isAlive():
        downscaling.join(timeout=1.0)

if __name__ == "__main__":
    main()

