from utils import LatLng, haversine
from .Entity import EntityBase, WithId


class Road(EntityBase, metaclass=WithId):
    def __init__(
        self,
        start: LatLng,
        end: LatLng,
        next_road: "Road" = None,
    ):
        super().__init__()
        self.id = next(self._ids)
        self.start = start
        self.end = end
        self.next_road: Road = next_road
        self.prev_road: Road = None

        if next_road is not None:
            next_road.set_prev_road(self)

    @property
    def length(self) -> float:
        """Returns length of the road in km"""
        return haversine(self.start, self.end)

    def set_next_road(self, road: "Road"):
        self.next_road = road
        road.set_prev_road(self)

    def set_prev_road(self, road: "Road"):
        self.prev_road = road
