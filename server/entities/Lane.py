import simpy
from .Entity import SimulationEntity


class Lane:
    def __init__(self, env: simpy.Environment, next_lane: "Lane" = None):
        self.env = env
        self.next = next_lane
        self.queue = []

    @property
    def last(self):
        return self.queue[0]

    @property
    def first(self):
        return self.queue[-1]

    def put(self, car: SimulationEntity):
        self.queue.insert(0, car)

    def pop(self, car: SimulationEntity):
        if self.first.id == car.id:
            return self.queue.pop()

    def get_car_position(self, car: SimulationEntity):
        return self.queue.index(car)
