from utils import LatLng, haversine


class Road:
    def __init__(
        self,
        id: int,
        start: LatLng,
        end: LatLng,
        next_road: "Road" = None,
    ):
        self.id = id
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
