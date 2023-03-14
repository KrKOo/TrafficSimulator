from .Entity import SimulationEntity, EntityBase, WithId
from utils import Turn


class Lane(EntityBase, metaclass=WithId):
    def __init__(
        self,
        is_forward: bool = True,
        turns: list[Turn] = None,
    ):
        super().__init__()
        self.id = next(self._ids)
        self.is_forward = is_forward
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
