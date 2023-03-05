from enum import Enum
import simpy
import math
import random
from .Way import Way
from .Entity import SimulationEntity
from utils import LatLng

MIN_GAP = 0.001


class CarState(Enum):
    Crossing = 1
    Queued = 2


class Car(SimulationEntity):
    def __init__(
        self,
        env: simpy.Environment,
        way: Way,
        lane_id: int,
        speed: int,
        length: int = 0.003,
    ):
        SimulationEntity.__init__(self, env)
        self.way = way
        self.lane = way.lanes[lane_id]
        self.desired_speed = speed  # in km/h
        self.speed = speed  # in km/h
        self.length = length  # in km
        self._position = 0  # in km
        self.update_time = 0  # in seconds
        self.state = CarState.Crossing
        self.lane.put(self)

        self.drive_proc = env.process(self.drive())

    @property
    def position(self) -> float:
        return self._position + self.speed * ((self.env.now - self.update_time) / 3600)

    @position.setter
    def position(self, value):
        self._position = value
        self.update_time = self.env.now

    @property
    def way_percentage(self) -> float:
        """Return the percentage of the way the car is on"""
        p = self.position / self.way.length

        if self.lane.is_forward == False:
            p = 1 - p

        return p * 100

    @property
    def is_first_in_lane(self) -> bool:
        queue_position = self.lane.get_car_position(self)
        if queue_position == len(self.lane.queue) - 1:
            return True
        return False


    #TODO: check for cars behind the crossroad
    @property
    def car_ahead(self) -> "Car":
        queue_position = self.lane.get_car_position(self)
        if not self.is_first_in_lane:
            return self.lane.queue[queue_position + 1]
        else:
            return None

    @property
    def lane_end_time(self) -> float:
        if self.speed == 0:
            return math.inf

        end_time = (self.way.length - self.position) / self.speed
        return end_time

    @property
    def lane_leave_time(self) -> float:
        if self.speed == 0:
            return math.inf

        leave_time = (
            self.way.length - self.position + self.length + MIN_GAP
        ) / self.speed
        return leave_time

    @property
    def distance_to_car_ahead(self) -> float:
        car_ahead = self.car_ahead

        if car_ahead is None:
            return None

        if car_ahead.lane == self.lane:
            return car_ahead.position - self.position - (self.length + MIN_GAP)
        elif car_ahead.lane == self.lane.next:
            return (
                car_ahead.position
                + self.way.length
                - self.position
                - (car_ahead.length + MIN_GAP)
            )

    @property
    def time_to_reach_car_ahead(self) -> float:
        distance = self.distance_to_car_ahead
        if distance is None:  # no car ahead
            return math.inf

        if self.speed < self.car_ahead.speed:
            return math.inf

        return distance / (self.speed - self.car_ahead.speed)

    def drive(self):
        while True:
            current_queue_position = self.lane.get_car_position(self)

            if self.state == CarState.Crossing:
                catch_up_time = self.time_to_reach_car_ahead
                if catch_up_time < self.lane_end_time:
                    # time to reach the car ahead
                    yield self.env.timeout(catch_up_time * 3600)

                    if self.car_ahead.lane == self.lane:
                        self.position = self.car_ahead.position - (
                            self.car_ahead.length + MIN_GAP
                        )
                    else:
                        size_in_previous_lane = (
                            self.car_ahead.length + MIN_GAP
                        ) - self.car_ahead.position
                        self.position = self.way.length - size_in_previous_lane

                    self.update_time = self.env.now
                    self.state = CarState.Queued
                    self.speed = self.car_ahead.speed
                    print(
                        f"Car {self.id} reached the car ahead {self.car_ahead.id} at {self.env.now} seconds, pos: {self.position} km, ahead_pos: {self.car_ahead.position}, speed: {self.speed} km/h"
                    )

            elif self.state == CarState.Queued:
                self.speed = self.car_ahead.speed

                if self.speed > self.desired_speed:
                    self.speed = self.desired_speed
                    self.state = CarState.Crossing

                    print(
                        f"Car {self.id} left the queue at {self.env.now} seconds, car {self.car_ahead.id} is too fast ({self.car_ahead.speed} km/h)"
                    )

            print(
                f"Car {self.id} is at {self.way_percentage}%, speed: {self.speed} km/h, time: {self.env.now} seconds"
            )
            yield self.env.timeout(self.lane_end_time * 3600)
            print(
                f"Car {self.id} reached the end of the way {self.way.id} at {self.env.now} seconds, way length: {self.way.length} km, at {self.way_percentage}%"
            )

            crossroad = self.way.next_crossroad if self.lane.is_forward else self.way.prev_crossroad
            next_options = crossroad.get_next_options(self.way)

            # TODO: A* instead of random ;)
            next_option = random.choice(next_options)
            next_way = next_option.way
            next_lane = random.choice(next_option.lanes)

            self.way = next_way
            self.lane.pop(self)
            self.lane = next_lane
            self.lane.put(self)
            self.position = 0
