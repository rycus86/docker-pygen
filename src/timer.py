import threading
import time

from utils import get_logger

logger = get_logger('pygen-timer')


class NotificationTimer(object):
    def __init__(self, timer_function, min_interval, max_interval):
        self.function = timer_function
        self.min_interval = min_interval
        self.max_interval = max_interval

        self.timer = None
        self.due_time = -1

    def schedule(self):
        logger.debug('Scheduling a notification')

        if self.min_interval <= 0:
            logger.debug('Sending notification immediately as interval is not greater than 0')

            # run the task immediately
            self.function()
            return

        # when is the current Timer due to start
        time_to_start = self.due_time - time.time()

        # if we never had a Timer before
        #   or there was and it is already finished
        #   or the start time has already passed
        # then just start another one
        if self.timer is None or self.timer.finished.is_set() or time_to_start < 0:
            logger.debug('The last timer started is due in %.2f seconds', time_to_start)

            # it is due in max_interval seconds from now the latest
            self.due_time = time.time() + self.max_interval

            # create and start a new Timer
            self.timer = threading.Timer(self.min_interval, self.function)
            self.timer.start()

            logger.debug('Started new timer due in %.2f-%.2f seconds', self.min_interval, self.max_interval)

        else:
            logger.debug('Cancelling pending timer to start a new one')

            # otherwise we have a Timer that has not run yet, cancel that
            self.timer.cancel()

            # the due time does not change so the Timer interval is
            #   that time at the latest or min_interval the earliest
            interval = min(self.min_interval, max(0, time_to_start))

            # create and start a new Timer
            self.timer = threading.Timer(interval, self.function)
            self.timer.start()

            logger.debug('Restarted the timer to run in %.2f-%.2f seconds', interval, time_to_start)
