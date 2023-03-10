from .Entity import SimulationEntity, EntityBase
from utils import Turn
from typing import List


class Lane(EntityBase):
    def __init__(
        self,
        is_forward: bool = True,
        next_lanes: List["Lane"] = None,
        turns: List[Turn] = None,
    ):
        super().__init__()

        self.is_forward = is_forward
        self.next = next_lanes  # TODO: Remove
        self.turns = turns

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
