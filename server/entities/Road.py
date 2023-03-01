from typing import List
from utils import LatLng, haversine

from .Lane import Lane


class RoadLanes:
    def __init__(self, forward: List[Lane], backward: List[Lane]):
        self.forward = forward
        self.backward = backward

        for lane in self.forward:
            lane.is_forward = True

        for lane in self.backward:
            lane.is_forward = False

    def __getitem__(self, index):
        lanes = self.forward + self.backward
        return lanes[index]


class Road:
    def __init__(
        self,
        id: int,
        start: LatLng,
        end: LatLng,
        max_speed: int,
        lanes: RoadLanes,
        oneway: bool = False,
        next_road: "Road" = None,
    ):
        self.id = id
        self.start = start
        self.end = end
        self.max_speed = max_speed
        self.oneway = oneway
        self.next_road = next_road
        self.prev_road = None
        self.lanes = lanes

        self._init_next_lanes()
        if next_road is not None:
            next_road.set_prev_road(self)

    @property
    def length(self):
        """Returns length of the road in km"""
        # return haversine(self.start, self.end) TODO: uncomment
        return 10

    def set_next_road(self, road: "Road"):
        self.next_road = road
        self._init_next_lanes()
        road.set_prev_road(self)

    def set_prev_road(self, road: "Road"):
        self.prev_road = road
        self._init_next_lanes()

    def _init_next_lanes(self):
        if self.next_road is None or self.prev_road is None:
            return

        assert len(self.lanes.forward) == len(self.next_road.lanes.forward)
        for idx, lane in enumerate(self.lanes.forward):
            lane.next = self.next_road.lanes.forward[idx]

        assert len(self.lanes.backward) == len(self.prev_road.lanes.backward)
        for idx, lane in enumerate(self.lanes.backward):
            lane.next = self.prev_road.lanes.backward[idx]
