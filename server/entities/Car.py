from enum import Enum
import simpy
import math
import random
from .Way import Way
from .Entity import SimulationEntity, WithId
from .Event import Event
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

        self.dequeue_event: simpy.Event = None
        self.crossing_end_event: simpy.Event = None
        self.car_ahead_updated_event: simpy.Event = None

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
        self.position = self.position
        self._speed = value

        print(
            f"Car {self.id} speed set to {self.speed}, position: {self.position}, time: {self.env.now}"
        )

        if self.car_behind:
            if (
                self.car_behind.car_ahead_updated_event
                and not self.car_behind.car_ahead_updated_event.triggered
            ):
                self.car_behind.car_ahead_updated_event.succeed()

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
            return car_ahead.position - self.position - (car_ahead.length + MIN_GAP)

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
                self.speed = self.desired_speed
                print(
                    f"Car {self.id} is crossing the way {self.way.id} at {self.position} km at {self.env.now}s, speed {self.speed} km/h"
                )

                if not self.is_first_in_lane:
                    crossing_time = self.env.timeout(
                        self.time_to_reach_car_ahead * 3600
                    )
                    self.car_ahead_updated_event = self.env.event()
                    yield crossing_time | self.car_ahead_updated_event

                    if self.car_ahead_updated_event.triggered:
                        self.position = self.position
                        self.state = CarState.Crossing
                    else:
                        self.position = self.position
                        self.state = CarState.Queued

                    self.car_ahead_updated_event = None
                else:
                    yield self.env.timeout(self.lane_end_time * 3600)
                    self.position = self.way.length
                    self.state = CarState.Waiting

                self.calendar_car_update()
            elif self.state == CarState.Queued:
                self.speed = min(self.car_ahead.speed, self.desired_speed)
                print(
                    f"Car {self.id} is queued on the way {self.way.id} at {self.position} after car {self.car_ahead.id} at {self.car_ahead.position} km at {self.env.now}s, speed {self.speed}km/h"
                )
                self.car_ahead_updated_event = self.env.event()
                yield self.car_ahead_updated_event

                if self.car_ahead:
                    self.state = CarState.Queued  # just update the speed
                else:
                    self.state = CarState.Crossing

                    print(
                        f"Car {self.id} is dequeued at {self.env.now}s, pos: {self.position}"
                    )
            elif self.state == CarState.Waiting:
                self.speed = 0
                print(
                    f"Car {self.id} is waiting on crossroad {self.next_crossroad.id} at {self.position} km at {self.env.now}s"
                )
                if self._next_lane is None:
                    return

                blockers = self.next_crossroad.get_conflicting_lane_blockers(
                    (self.way, self.lane), (self._next_way, self._next_lane)
                )

                blocker_requests = [blocker.request() for blocker in blockers]

                for blocker_request in blocker_requests:
                    yield blocker_request

                if self.car_behind:
                    if (
                        self.car_behind.car_ahead_updated_event
                        and not self.car_behind.car_ahead_updated_event.triggered
                    ):
                        self.car_behind.car_ahead_updated_event.succeed()

                self.way = None
                self.lane.pop(self)

                if self._next_lane.last:
                    print(
                        f"{self.id}, Car in next lane {self._next_lane.last.id}, {self._next_lane.last.position}, {self._next_lane.last.speed}"
                    )
                    while (
                        self._next_lane.last
                        and self._next_lane.last.position < MIN_GAP + self.length
                    ):
                        yield self.env.timeout(1)  # waiting for space

                print(
                    f"Car {self.id} turning to way {self._next_way.id}/{self._next_way.osm_id}, {self._next_turn}"
                )
                self.way = self._next_way

                self.lane = self._next_lane
                self.lane.put(self)

                for idx, blocker in enumerate(blockers):
                    blocker.release(blocker_requests[idx])

                self.position = 0

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
                self.id,
                self.way.id,
                self.lane.id,
                self.position,
                self.speed,
            )
        )
