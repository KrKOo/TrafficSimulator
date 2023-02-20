from utils import LatLng, haversine
from simpy import Store, Environment


class Lane:
    def __init__(self, env: Environment, next_lane: "Lane" = None):
        self.env = env
        self.next = next_lane
        self.queue = []

    def put(self, car):
        self.queue.insert(0, car)

    def get(self):
        return self.queue.pop()

    def get_car_position(self, car):
        # return self.queue.index(car)
        for i, c in enumerate(self.queue):
            if c.id == car.id:
                return i



class Road:
    def __init__(
        self,
        env: Environment,
        start: LatLng,
        end: LatLng,
        max_speed: int,
        lane_count: int,
        oneway: bool = False,
        next_road: "Road" = None,
    ):
        self.env = env
        self.start = start
        self.end = end
        self.max_speed = max_speed
        self.lane_count = lane_count
        self.oneway = oneway
        self.next_road = next_road
        self.length = self.__get_length()
        self.lanes = self.__init_lanes()
        # TODO: forward/backward lanes

    def __get_length(self):
        """Returns length of the road in km"""
        # return haversine(self.start, self.end)
        return 10

    def __init_lanes(self):
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
