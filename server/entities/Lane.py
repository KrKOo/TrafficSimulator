import simpy
from .Entity import SimulationEntity


class Lane:
    def __init__(self, env: simpy.Environment, next_lane: "Lane" = None):
        self.env = env
        self.next = next_lane
        self.queue = []

    def put(self, car: SimulationEntity):
        self.queue.insert(0, car)

    def get(self):
        return self.queue.pop()

    def get_car_position(self, car: SimulationEntity):
        return self.queue.index(car)
