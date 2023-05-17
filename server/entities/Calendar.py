import simpy

from .CarEvent import CarEvent
from .CrossroadEvent import CrossroadEvent


class Calendar:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.car_events: list[CarEvent] = []
        self.crossroad_events: list[CrossroadEvent] = []

    def add_car_event(self, event: CarEvent):
        event.time = float(self.env.now)
        self.car_events.append(event)

    def add_crossroad_event(self, event):
        event.time = float(self.env.now)
        self.crossroad_events.append(event)

    def pack(self):
        car_events_bytes = b"".join([event.pack() for event in self.car_events])
        crossroad_events_bytes = b"".join(
            [event.pack() for event in self.crossroad_events]
        )

        return (car_events_bytes + crossroad_events_bytes), (
            len(self.car_events),
            len(self.crossroad_events),
        )

    def get_data(self):
        car_events = [event.get_data() for event in self.car_events]
        crossroad_events = [event.get_data() for event in self.crossroad_events]
        return {"car_events": car_events, "crossroad_events": crossroad_events}
