import datetime
import time
import abc
import threading

from queue import Queue

import RPi.GPIO as gpio


class Door(object):

    STATE_OPEN = 1
    STATE_CLOSED = 0
    STATE_IN_BETWEEN = -1

    door_name = None
    door_gps_coords = None
    top_gpio = None
    bottom_gpio = None
    relay_gpio = None

    # approximate time for door to close or open
    action_time = None

    action_queue = None

    def __init__(self, config):
        self.door_name = config.door_name
        if config.door_gps_coords:
            self.door_gps_coords = config.door_gps_coords
        self.top_gpio = config.top_gpio
        self.bottom_gpio = config.bottom_gpio
        self.relay_gpio = config.relay_gpio
        self.action_time = config.action_time
        self.action_queue = Queue()

    @property
    def state(self):
        if gpio.input(self.top_gpio) == 0:
            return Door.STATE_OPEN
        elif gpio.input(self.bottom_gpio) == 0:
            return Door.STATE_CLOSED
        else:
            return Door.STATE_IN_BETWEEN

    def open_door(self):
        if self.state == Door.STATE_OPEN:
            self.action_queue.put(GarageActionMessage('Door is already open', 'derek'))
            return
        elif self.state == Door.STATE_CLOSED:
            # create a message to add to the queue
            self.action_queue.put(GarageActionMessage('Opening door', 'derek'))
            if self._perform_door_action(Door.STATE_OPEN):
                self.action_queue.put(GarageActionMessage('Door opened', 'derek'))
            else:
                self.action_queue.put(GarageActionMessage('Door failed to open', 'derek'))
        elif self.state == Door.STATE_IN_BETWEEN:
            # door is in motion, wait for time then check state
            time.sleep(self.action_time)

            if self.state == Door.STATE_OPEN:
                self.action_queue.put(GarageActionMessage('Door is already open', 'derek'))
                return
            elif self.state == Door.STATE_CLOSED:
                if self._perform_door_action(Door.STATE_OPEN):
                    self.action_queue.put(GarageActionMessage('Door opened', 'derek'))
                else:
                    self.action_queue.put(GarageActionMessage('Door failed to open', 'derek'))
            else:
                # door is in between
                    self.action_queue.put(GarageActionMessage('Door open action cannot be performed', 'derek'))

    def close_door(self):
        if self.state == Door.STATE_CLOSED:
            self.action_queue.put(GarageActionMessage('Door is already closed', 'derek'))
            return
        elif self.state == Door.STATE_OPEN:
            # create a message to add to the queue
            self.action_queue.put(GarageActionMessage('Closing door', 'derek'))
            if self._perform_door_action(Door.STATE_CLOSED):
                self.action_queue.put(GarageActionMessage('Door closed', 'derek'))
            else:
                self.action_queue.put(GarageActionMessage('Door failed to close', 'derek'))
        elif self.state == Door.STATE_IN_BETWEEN:
            # door is in motion, wait for time then check state
            time.sleep(self.action_time)

            if self.state == Door.STATE_CLOSED:
                self.action_queue.put(GarageActionMessage('Door is already closed', 'derek'))
                return
            elif self.state == Door.STATE_OPEN:
                if self._perform_door_action(Door.STATE_CLOSED):
                    self.action_queue.put(GarageActionMessage('Door closed', 'derek'))
                else:
                    self.action_queue.put(GarageActionMessage('Door failed to close', 'derek'))
            else:
                # door is in between
                self.action_queue.put(GarageActionMessage('Door close action cannot be performed', 'derek'))

    def _perform_door_action(self, action_to_perform):
        gpio.output(self.relay_gpio, False)
        time.sleep(0.2)
        gpio.output(self.relay_gpio, True)

        time.sleep(self.action_time)

        if self.state == action_to_perform:
            return True
        else:
            return False


class GarageActionMessage(object):
    action_time = None
    message = None
    initiated_by = None

    def __init__(self, message, initiated_by):
        self.message = message
        self.initiated_by = initiated_by
        action_time = datetime.datetime.now()

    def __repr__(self):
        return '<GarageActionMessage> {}'.format(self.message)


class GarageMessangerBase(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def initialize(self, config):
        return

    @abc.abstractmethod
    def send_message(self, action_message):
        return


if __name__ == '__main__':
    garage_message_queue = Queue()
