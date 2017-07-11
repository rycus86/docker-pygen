import threading
import time


class NotificationTimer(object):
    def __init__(self, timer_function, min_interval, max_interval):
        self.function = timer_function
        self.min_interval = min_interval
        self.max_interval = max_interval

        self.timer = None
        self.due_time = -1

    def schedule(self):
        if self.min_interval <= 0 or self.max_interval <= 0:
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
            # it is due in max_interval seconds from now the latest
            self.due_time = time.time() + self.max_interval

            # create and start a new Timer
            self.timer = threading.Timer(self.min_interval, self.function)
            self.timer.start()

        else:
            # otherwise we have a Timer that has not run yet, cancel that
            self.timer.cancel()

            # the due time does not change so the Timer interval is
            #   that time at the latest or min_interval the earliest
            interval = min(self.min_interval, max(0, self.due_time - time.time()))

            # create and start a new Timer
            self.timer = threading.Timer(interval, self.function)
            self.timer.start()
