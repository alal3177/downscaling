import logging
import random
from threading import Thread
import time

LOG = logging.getLogger(__name__)

class FailureSimulator(Thread):

    def __init__(self, stop_event, config, workers, interval=240):

        Thread.__init__(self)
        self.stop_event = stop_event
        self.config = config
        self.workers = workers
        self.interval = interval

    def run(self):

        LOG.info("Activating Failure Simulator. Sleep period: %d sec" % (self.interval))
        while(not self.stop_event.is_set()):
            #time.sleep(self.interval)
            self.stop_event.wait(self.interval)

            count = len(self.workers.list)
            if count > 0:
                pick = random.randint(0, count-1)
                worker = self.workers.list[pick]
                worker.terminate()
                del self.workers.list[pick]
                LOG.info("Failure Simulator terminated an instance %s (%s)" % (worker.instance_id, worker.dns))
            else:
                LOG.info("No instances to kill. Terminating Failure Simulator")
                self.stop_event.set()