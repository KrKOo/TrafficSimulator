from typing import List
from utils import LatLng, haversine
from simpy import Environment

from .Lane import Lane


class Road:
    def __init__(
        self,
        id: int,
        env: Environment,
        start: LatLng,
        end: LatLng,
        max_speed: int,
        lane_count: int,
        oneway: bool = False,
        next_road: "Road" = None,
    ):
        self.id = id
        self.env = env
        self.start = start
        self.end = end
        self.max_speed = max_speed
        self.lane_count = lane_count
        self.oneway = oneway
        self.next_road = next_road
        self.lanes = self._init_lanes()
        # TODO: forward/backward lanes

    @property
    def length(self):
        """Returns length of the road in km"""
        # return haversine(self.start, self.end) TODO: uncomment
        return 10

    def _init_lanes(self) -> List[Lane]:
        """Initializes the list of simpy containers representing the lanes"""

        lanes = []
        for i in range(self.lane_count):
            # TODO: handle different lane counts
            if self.next_road is None:
                lanes.append(Lane(self.env))
            else:
                lanes.append(Lane(self.env, self.next_road.lanes[i]))
        return lanes

    def set_next_road(self, road: "Road"):
        self.next_road = road
        for idx, lane in enumerate(self.lanes):
            lane.next = road.lanes[idx]
