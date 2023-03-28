from enum import Enum
import simpy
import math
import random
from .Way import Way
from .Entity import SimulationEntity, WithId
from .Event import Event, EventType
from .Calendar import Calendar
from .Lane import Lane
from .Crossroad import Crossroad
from utils import Turn

MIN_GAP = 0.001


class CarState(Enum):
    Crossing = 1
    Queued = 2
    Waiting = 3


class Car(SimulationEntity, metaclass=WithId):
    def __init__(
        self,
        env: simpy.Environment,
        calendar: Calendar,
        way: Way,
        lane_id: int,
        speed: int,
        length: int = 0.003,
    ):
        SimulationEntity.__init__(self, env)
        self.id = next(self._ids)
        self.calendar = calendar
        self.way = way
        self.lane = way.lanes[lane_id]
        self.desired_speed = speed  # in km/h
        self._speed = speed  # in km/h
        self.length = length  # in km
        self._position = 0  # in km
        self.update_time = 0  # in seconds
        self.state = CarState.Crossing
        self.lane.put(self)

        self._next_way = None
        self._next_lane = None
        self._next_turn = None

        next_path = self._get_next_path()
        self._next_way, self._next_lane, self._next_turn = (
            next_path if next_path else (None, None, None)
        )

        self.drive_proc = env.process(self.drive())

        self.calendar_car_update()

    def __repr__(self):
        return (
            f"Car id: {self.id} way: {self.way.id}, lane: {self.lane.id}, position: {self.position}, speed: {self.speed}, "
            f"state: {self.state}, next_way: {self._next_way.id if self._next_way else None}, next_lane: {self._next_lane.id if self._next_lane else None}, "
            f"car_ahead: {self.car_ahead.id if self.car_ahead else None}, car_behind: {self.car_behind.id if self.car_behind else None}"
        )

    @property
    def position(self) -> float:
        return self._position + self.speed * ((self.env.now - self.update_time) / 3600)

    @position.setter
    def position(self, value):
        self._position = value
        self.update_time = self.env.now

    @property
    def speed(self) -> int:
        return self._speed

    @speed.setter
    def speed(self, value):
        self._speed = value

        if self.car_behind and self.car_behind.state == CarState.Queued:
            car_behind = self.car_behind
            car_behind.speed = value
            if car_behind.speed > car_behind.desired_speed:
                car_behind.speed = car_behind.desired_speed
                car_behind.state = CarState.Crossing
                self.drive()

    @property
    def way_percentage(self) -> float:
        """Return the percentage of the way the car is on"""
        p = self.position / self.way.length

        if self.lane.is_forward == False:
            p = 1 - p

        return abs(round(p * 100, 4))

    @property
    def is_first_in_lane(self) -> bool:
        return self == self.lane.first

    @property
    def is_last_in_lane(self) -> bool:
        return self == self.lane.last

    @property
    def car_ahead(self) -> "Car":
        queue_position = self.lane.get_car_position(self)
        if not self.is_first_in_lane:
            return self.lane.queue[queue_position + 1]

    @property
    def car_behind(self) -> "Car":
        queue_position = self.lane.get_car_position(self)
        if not self.is_last_in_lane:
            return self.lane.queue[queue_position - 1]

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
            # return car_ahead.position - self.position - (car_ahead.length + MIN_GAP)
            return car_ahead.position - self.position  # TODO: FIX

    @property
    def time_to_reach_car_ahead(self) -> float:
        distance = self.distance_to_car_ahead
        if distance is None:  # no car ahead
            return math.inf

        if self.speed <= self.car_ahead.speed:
            return math.inf

        return distance / (self.speed - self.car_ahead.speed)

    @property
    def next_crossroad(self) -> Crossroad:
        return (
            self.way.next_crossroad if self.lane.is_forward else self.way.prev_crossroad
        )

    def drive(self):
        while True:
            if self.state == CarState.Crossing:
                catch_up_time = self.time_to_reach_car_ahead

                if catch_up_time < self.lane_end_time:
                    # time to reach the car ahead
                    yield self.env.timeout(catch_up_time * 3600)
                    self.position = self.position + catch_up_time * self.speed

                    self.state = CarState.Queued
                    break
                else:
                    yield self.env.timeout(self.lane_end_time * 3600)
                    self.position = self.way.length
                    self.state = CarState.Waiting
                    self.speed = 0

                self.calendar_car_update()
            elif self.state == CarState.Waiting:
                if self._next_lane is None:
                    return

                wait_start = self.env.now
                blockers = self.next_crossroad.get_conflicting_lane_blockers(
                    (self.way, self.lane), (self._next_way, self._next_lane)
                )

                blocker_requests = [blocker.request() for blocker in blockers]

                for blocker_request in blocker_requests:
                    yield blocker_request

                wait_end = self.env.now

                if wait_end - wait_start > 0:
                    print("WAITED on crossroad: ", wait_end - wait_start)

                self.way = self._next_way

                self.lane.pop(self)
                self.lane = self._next_lane
                self.lane.put(self)

                yield self.env.timeout(10)  # passing the crossroad

                for idx, blocker in enumerate(blockers):
                    blocker.release(blocker_requests[idx])

                self.position = 0
                self.speed = (
                    self.desired_speed
                )  # TODO: check if there is free space after the crossroad
                self.state = CarState.Crossing

                next_path = self._get_next_path()
                self._next_way, self._next_lane, self._next_turn = (
                    next_path if next_path else (None, None, None)
                )

                self.calendar_car_update()

    def _get_next_path(self) -> tuple[Way, Lane, Turn]:
        crossroad = self.next_crossroad

        next_way_options = crossroad.get_next_way_options(self.way)
        turn = None

        # Turn back if no other option
        if len(next_way_options) == 0:
            next_way = self.way
            next_lanes = (
                next_way.lanes.backward
                if self.lane.is_forward
                else next_way.lanes.forward
            )

            if len(next_lanes) == 0:
                return None

            next_lane = random.choice(next_lanes)
        else:
            next_way_option = random.choice(next_way_options)
            next_way = next_way_option.way
            turn = next_way_option.turn
            lane_options = crossroad.get_next_lane_options(self.way, next_way)
            if self.lane not in lane_options.keys():
                # TODO: check if the car can switch lanes
                lane_to_switch = random.choice(list(lane_options.keys()))

                self.calendar_car_update()

                self.lane.pop(self)
                self.lane = lane_to_switch
                self.lane.put(self)

            next_lane = random.choice(lane_options[self.lane])

        return next_way, next_lane, turn

    def calendar_car_update(self):
        self.calendar.add_event(
            Event(
                EventType.CarUpdate,
                self.id,
                self.way.id,
                self.lane.id,
                self.position,
                self.speed,
            )
        )
