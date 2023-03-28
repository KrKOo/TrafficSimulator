import simpy

from .Event import Event

counter = 0

class Calendar:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.events = []

    def add_event(self, event: Event):
        event.time = float(self.env.now)
        self.events.append(event)

    def pack(self):
        return b''.join([event.pack() for event in self.events])

    def get_data(self):
        return [event.get_data() for event in self.events]
