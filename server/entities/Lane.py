import struct
from .Entity import SimulationEntity, EntityBase, WithId
from entities import Way, Car
from utils import Turn, LatLng
from utils.math import haversine


class Lane(EntityBase, metaclass=WithId):
    def __init__(
        self,
        nodes,
        way: Way = None,
        is_forward: bool = True,
        turns: list[Turn] = None,
    ):
        super().__init__()
        self.id = next(self._ids)
        self.is_forward = is_forward
        self.turns = turns if turns is not None else []
        self.nodes: list[LatLng] = nodes
        self.way: Way = way
        self.length = self._get_length()

        # Neighbour lanes
        self.right: Lane = None
        self.left: Lane = None

        self.queue: list[Car] = []

    def _get_length(self):
        length = 0
        for i in range(len(self.nodes) - 1):
            length += haversine(self.nodes[i], self.nodes[i + 1])

        return length

    @property
    def last(self):
        return self.queue[0] if len(self.queue) > 0 else None

    @property
    def first(self):
        return self.queue[-1] if len(self.queue) > 0 else None

    def put(self, car: SimulationEntity):
        self.queue.insert(0, car)

    def put_ahead_of_car(self, car: SimulationEntity, car_behind: SimulationEntity):
        self.queue.insert(self.queue.index(car_behind) + 1, car)

    def pop(self, car: SimulationEntity):
        if self.first.id == car.id:
            return self.queue.pop()

    def remove(self, car: SimulationEntity):
        if car in self.queue:
            self.queue.remove(car)

    def get_car_position(self, car: SimulationEntity):
        return self.queue.index(car)

    def get_car_behind_position(self, position: float):
        car_behind = None
        for car in self.queue:
            if car.position < position:
                car_behind = car
            else:
                break

        return car_behind

    def get_car_ahead_of_position(self, position: float):
        for car in self.queue:
            if car.position > position:
                return car

        return None

    def pack(self):
        nodes_list = []

        for node in self.nodes:
            nodes_list.append(struct.pack("!ff", node.lat, node.lng))

        lane_struct = struct.Struct("!II?????????")

        lane_bytes = lane_struct.pack(
            self.id,
            len(nodes_list),
            self.is_forward,
            Turn.none in self.turns,
            Turn.left in self.turns,
            Turn.right in self.turns,
            Turn.through in self.turns,
            Turn.merge_to_right in self.turns,
            Turn.merge_to_left in self.turns,
            Turn.slight_right in self.turns,
            Turn.slight_left in self.turns,
        )
        return lane_bytes + b"".join(nodes_list)
