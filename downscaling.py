#!/usr/bin/env python

import logging
import signal
import time
from threading import Thread, Event

from lib.logger import configure_logging
from lib.util import parse_options
from lib.config import Config
from resources.clouds import Clouds
from resources.master import Master
from resources.workers import Workers
from resources.workload import Workload
from resources.initialmonitor import InitialMonitor
from resources.replacer import Replacer
from lib.util import Command
from resources.policy import Policy

SIGEXIT = False
LOG = logging.getLogger(__name__)

class Downscaling(Thread):
    def __init__(self, config):

        Thread.__init__(self)
        self.config = config

    def run(self):
        LOG.info("Starting Downscaling")
        #TODO(dmdu): do something

        # Get information about available clouds
        self.clouds = Clouds(self.config)

        # Potentially terminate some/all instances from the previous experiment
        self.clouds.selected_terminate()

        # Launch master and worker nodes
        self.master = Master(self.config, self.clouds)
        self.workers = Workers(self.config, self.clouds, self.master)
        self.workers.create()

        # Wait until all workers register with master (as Idle resources)
        self.initialmonitor = InitialMonitor(self.config, self.master, self.workers.total_number)
        self.initialmonitor.start()

        # While waiting for initial monitor, copy config files to the log directory for current experiment
        command = "cp etc/* %s/" % (self.config.log_dir)
        cmd = Command(command)
        code = cmd.execute()
        if code == 0:
            LOG.info("Config files have been copied successfully to the log directory")
        # Copy workload (def: parsing/condor.submit) file to the log directory
        command = "cp %s %s/" % (self.config.workload.submit_local, self.config.log_dir)
        cmd = Command(command)
        code = cmd.execute()
        if code == 0:
            LOG.info("Workload file has been copied successfully to the log directory")

        self.initialmonitor.join()

        # Submit and execute workload
        self.workload = Workload(self.config, self.master)
        self.workload.execute()

        time.sleep(30)

        # Launch replacer and failure simulator
        self.replacer_stop= Event()
        self.replacer = Replacer(self.replacer_stop, self.config, self.master, interval=120)
        self.replacer.start()

        # Start downscaling policy
        self.policy = Policy(self.config, self.master)
        self.policy.start()

        # Sleep while the replacer is running (while there are jobs in the queue)
        while self.replacer.isAlive():
            time.sleep(5)

        # Stop downscaling policy
        self.policy.stop()

        # Copy the master log back
        self.workload.get_log()
        # Terminate some/all instances
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

