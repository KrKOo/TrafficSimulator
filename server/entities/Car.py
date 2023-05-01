from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from modules import VehicleSpawner

from enum import Enum
import simpy
from simpy.util import start_delayed
import math
import random

from .Way import Way
from .Entity import SimulationEntity, WithId
from .Event import Event
from .Calendar import Calendar
from .Lane import Lane
from .Crossroad import Crossroad
from utils import Turn, LatLng
from utils.math import haversine

MIN_GAP = 0.001
CROSSROAD_BLOCKING_TIME = (
    3  # block the crossroad when the car will reach it in this time
)


class CarState(Enum):
    Crossing = 1
    Queued = 2
    Waiting = 3


class Car(SimulationEntity, metaclass=WithId):
    def __init__(
        self,
        env: simpy.Environment,
        spawner: "VehicleSpawner",
        calendar: Calendar,
        way: Way,
        lane_id: int,
        speed: int,
        length: int = 0.003,
    ):
        SimulationEntity.__init__(self, env)
        self.id = next(self._ids)
        self.spawner = spawner
        self.calendar = calendar
        self._way = way
        self.lane = way.lanes[lane_id]
        self.desired_speed = speed  # in km/h
        self._speed = speed  # in km/h
        self.length = length  # in km
        self._position = 0  # in km
        self.update_time = self.env.now  # in seconds
        self.state = CarState.Crossing
        self.lane.put(self)

        self._next_way = None
        self._next_lane = None
        self._next_turn = None

        next_path = self._get_next_path()
        self._next_way, self._next_lane, self._next_turn = (
            next_path if next_path else (None, None, None)
        )

        self._crossroad_blockers: list[list[simpy.Resource]] = []
        self._blocker_requests: list[list[simpy.Request]] = []
        self._next_crossroad_blocked = False
        self._crossroad_unblock_proc = None

        self.dequeue_event: simpy.Event = None
        self.crossing_end_event: simpy.Event = None
        self.car_ahead_updated_event: simpy.Event = None

        self.controller_proc = env.process(self.controller())

        self.calendar_car_update()

    def __repr__(self):
        return (
            f"Car id: {self.id} way: {self.way.id if self.way else None}, lane: {self.lane.id if self.lane else None}, position: {self.position}, speed: {self.speed}, "
            f"state: {self.state}, next_way: {self._next_way.id if self._next_way else None}, next_lane: {self._next_lane.id if self._next_lane else None}, "
            f"car_ahead: {self.car_ahead.id if self.car_ahead else None}, car_behind: {self.car_behind.id if self.car_behind else None}"
        )

    def controller(self):
        yield self.env.process(self.drive())
        self.despawn()

    @property
    def way(self) -> Way:
        return self._way

    @way.setter
    def way(self, value):
        self._way = value
        self._next_crossroad_blocked = (
            False  # TODO: might change when lane chaning is applied
        )
        self.env.process(self._unblock_crossroad())

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
        self.calendar_car_update()

        self.poke_car_behind(self.car_behind)

        if len(self._crossroad_blockers) > 1 or (
            not self._next_crossroad_blocked and len(self._crossroad_blockers) == 1
        ):
            if self._crossroad_unblock_proc:
                self._crossroad_unblock_proc.interrupt()
                self._crossroad_unblock_proc.defused = True
                self._crossroad_unblock_proc = None

            time_to_leave_crossroad = self.time_to_be_at_position(
                self.length + MIN_GAP + 0.0001
            )

            if time_to_leave_crossroad > 0:
                print(
                    f"Car {self.id} will unlock crossroad in {time_to_leave_crossroad} seconds"
                )
                self._crossroad_unblock_proc = start_delayed(
                    self.env, self._unblock_crossroad(), time_to_leave_crossroad
                )

    @property
    def way_percentage(self) -> float:
        """Return the percentage of the way the car is on"""
        p = self.position / self.lane.length

        # if self.lane.is_forward == False:
        #     p = 1 - p

        return abs(round(p * 100, 4))

    @property
    def is_first_in_lane(self) -> bool:
        return self == self.lane.first

    @property
    def is_last_in_lane(self) -> bool:
        return self == self.lane.last

    @property
    def car_ahead(self) -> "Car":
        if not self.is_first_in_lane:
            queue_position = self.lane.get_car_position(self)
            return self.lane.queue[queue_position + 1]

    @property
    def car_behind(self) -> "Car":
        if not self.is_last_in_lane:
            queue_position = self.lane.get_car_position(self)
            return self.lane.queue[queue_position - 1]

    @property
    def lane_end_time(self) -> float:
        if self.speed == 0:
            return math.inf

        end_time = (self.lane.length - self.position) / self.speed
        return end_time * 3600

    @property
    def lane_leave_time(self) -> float:
        if self.speed == 0:
            return math.inf

        leave_time = (
            self.lane.length - self.position + self.length + MIN_GAP
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

        return (distance / (self.speed - self.car_ahead.speed)) * 3600

    @property
    def next_crossroad(self) -> Crossroad:
        return (
            self.way.next_crossroad if self.lane.is_forward else self.way.prev_crossroad
        )

    def time_to_travel_distance(self, distance: float) -> float:
        if self.speed == 0:
            return math.inf

        return (distance / self.speed) * 3600

    def time_to_be_at_position(self, dest_position: float) -> float:
        """Returns negative time if the car is already past the dest_position"""
        return self.time_to_travel_distance(dest_position - self.position)

    @property
    def is_next_crossroad_blocked(self) -> bool:
        if self._next_way is None:
            return False

        blockers = self.next_crossroad.get_conflicting_lane_blockers(
            (self.way, self.lane), (self._next_way, self._next_lane)
        )

        print(
            f"Car {self.id} Crossroad {self.next_crossroad.id} blockers: {[blocker.count for blocker in blockers]}"
        )

        next_crossroad_blocker_requests = (
            self._blocker_requests[-1] if len(self._blocker_requests) > 0 else []
        )

        for blocker in blockers:
            if (
                blocker.count > 0
                and blocker.users[0] not in next_crossroad_blocker_requests
            ):
                return True

        return False

    def _block_next_crossroad(self):
        if self._next_way is None:
            return self.env.timeout(0)

        blockers = self.next_crossroad.get_conflicting_lane_blockers(
            (self.way, self.lane), (self._next_way, self._next_lane)
        )

        self._crossroad_blockers.append(blockers)

        blocker_requests = [blocker.request() for blocker in blockers]

        self._blocker_requests.append(blocker_requests)

        return self.env.all_of(blocker_requests)

    def _unblock_crossroad(self):
        if len(self._crossroad_blockers) == 0:
            self._crossroad_unblock_proc = None
            return

        blockers = self._crossroad_blockers.pop(0)
        blocker_requests = self._blocker_requests.pop(0)

        for idx, blocker in enumerate(blockers):
            blocker.release(blocker_requests[idx])

        self._crossroad_unblock_proc = None
        print(
            f"Car {self.id} Crossroad unblocked at {self.env.now}, {[blocker.count for blocker in blockers]}"
        )
        yield self.env.timeout(0)

    def _wait_and_block_crossroad(self):
        while self.is_next_crossroad_blocked:
            yield self.env.timeout(1)  # wait and try again

        print(f"Car {self.id} not waiting for timeout")
        yield self._block_next_crossroad()  # should be instant

    def despawn(self):
        self.speed = 0
        self.env.process(self._unblock_crossroad())
        car_behind = self.car_behind
        print("Car behind", car_behind)
        self.lane.remove(self)
        self.poke_car_behind(car_behind)
        self.spawner.despawn(self)
        print(f"Car {self.id} despawned, {[car.id for car in self.lane.queue]}")

    def poke_car_behind(self, car_to_poke):
        if car_to_poke:
            if (
                car_to_poke.car_ahead_updated_event
                and not car_to_poke.car_ahead_updated_event.triggered
            ):
                car_to_poke.car_ahead_updated_event.succeed()

    def drive(self):
        while True:
            if self.state == CarState.Crossing:
                self.speed = self.desired_speed

                if (
                    not self.is_first_in_lane
                    and self.time_to_reach_car_ahead != math.inf
                ):
                    if self.time_to_reach_car_ahead < 0:
                        print("colision")
                        return

                    crossing_timeout = self.env.timeout(self.time_to_reach_car_ahead)

                    print(
                        f"Car {self.id} is catching up {self.car_ahead.id}, time: {self.time_to_reach_car_ahead}, distance: {self.distance_to_car_ahead}, speed: {self.speed}"
                    )

                    self.car_ahead_updated_event = self.env.event()
                    yield crossing_timeout | self.car_ahead_updated_event

                    if self.car_ahead_updated_event.triggered:
                        self.position = self.position
                        self.state = CarState.Crossing
                    else:
                        self.position = self.position
                        self.state = CarState.Queued
                        print(
                            f"Car {self.id} caught up {self.car_ahead.id} at {self.position}/{self.lane.length}, {self.env.now}, way: {self.way.id}, lane: {self.lane.id}, ahead way: {self.car_ahead.way.id}, ahead lane: {self.car_ahead.lane.id}, ahead position: {self.car_ahead.position}/{self.car_ahead.lane.length}"
                        )

                    self.car_ahead_updated_event = None
                else:
                    close_to_crossroad_time = max(
                        self.lane_end_time - CROSSROAD_BLOCKING_TIME, 0
                    )

                    # Come close to the crossroad
                    print(
                        f"Car {self.id} coming close to crossroad {self.position}/{self.lane.length}, close_to_crossroad_time: {close_to_crossroad_time}"
                    )
                    self.car_ahead_updated_event = self.env.event()
                    yield self.env.timeout(
                        close_to_crossroad_time
                    ) | self.car_ahead_updated_event

                    if self.car_ahead_updated_event.triggered:
                        self.position = self.position
                        self.state = CarState.Crossing
                        self.car_ahead_updated_event = None
                        continue

                    # If the crossroad is clear, block the crossroad
                    print(
                        f"Car {self.id}, next crossroad blocked: {self.is_next_crossroad_blocked}, blockers {[blocker.count for blocker in self._crossroad_blockers]}"
                    )
                    if not self.is_next_crossroad_blocked and self.is_first_in_lane:
                        print(
                            f"Car {self.id} blocking near crossroad at {self.env.now}"
                        )
                        yield self._block_next_crossroad()  # should be instant
                        self._next_crossroad_blocked = True
                        print(f"Car {self.id} blocked near crossroad at {self.env.now}")

                    # Come to the crossroad (end of the way)
                    print(
                        f"Car {self.id} coming to the crossroad {self.position}/{self.lane.length}, lane_end_time: {self.lane_end_time}"
                    )
                    yield self.env.timeout(
                        self.lane_end_time
                    ) | self.car_ahead_updated_event

                    if self.car_ahead_updated_event.triggered:
                        self.position = self.position
                        self.state = CarState.Crossing
                        self.car_ahead_updated_event = None
                        continue

                    self.position = self.lane.length
                    self.state = CarState.Waiting

            elif self.state == CarState.Queued:
                self.speed = min(self.car_ahead.speed, self.desired_speed)
                self.car_ahead_updated_event = self.env.event()
                yield self.car_ahead_updated_event

                if self.car_ahead:  # TODO: check if it is the same car ahead
                    print(
                        f"Car ahead {self.car_ahead.id} updated, {[car.id for car in self.lane.queue]}"
                    )
                    self.state = CarState.Queued  # just update the speed
                else:
                    self.state = CarState.Crossing

            elif self.state == CarState.Waiting:
                self.speed = 0
                if self._next_lane is None:
                    return

                if not self._next_crossroad_blocked:
                    print(
                        f"Car {self.id} blocking crossroad {self.next_crossroad.id} at {self.env.now}"
                    )
                    yield self.env.process(self._wait_and_block_crossroad())
                    print(
                        f"Car {self.id} blocked crossroad {self.next_crossroad.id} at {self.env.now}"
                    )

                car_behind_in_prev_lane = self.car_behind

                self.lane.pop(self)
                self.way = self._next_way

                self.lane = self._next_lane
                self.lane.put(self)

                self.position = 0

                self.poke_car_behind(car_behind_in_prev_lane)

                self.state = CarState.Crossing

                next_path = self._get_next_path()
                self._next_way, self._next_lane, self._next_turn = (
                    next_path if next_path else (None, None, None)
                )

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

                self.lane.remove(self)
                self.lane = lane_to_switch
                self.lane.put(self)

            next_lane = random.choice(lane_options[self.lane])

        return next_way, next_lane, turn

    def get_coords(self):
        car_distance = self.position

        nodes_length = 0
        segment_length = None

        nodes = self.lane.nodes
        if not self.lane.is_forward:
            nodes.reverse()

        for i in range(len(self.way.nodes) - 1):
            segment_length = haversine(self.way.nodes[i].pos, self.way.nodes[i + 1].pos)
            nodes_length += segment_length

            if nodes_length > car_distance:
                break

        car_distance_on_segment = nodes_length - car_distance
        segment_percentage = car_distance_on_segment / segment_length

        lat = nodes[i].lat + (nodes[i + 1].lat - nodes[i].lat) * segment_percentage

        lng = nodes[i].lng + (nodes[i + 1].lng - nodes[i].lng) * segment_percentage

        return LatLng(lat, lng)

    def calendar_car_update(self):
        print(
            f"Car {self.id} updated at {self.env.now}, position {self.way_percentage}, speed {self.speed}, state {self.state.name}, way {self.way.id}, lane {self.lane.id}, car ahead {(self.car_ahead.id, self.car_ahead.way_percentage) if self.car_ahead else None}, car behind {self.car_behind.id if self.car_behind else None}"
        )
        self.calendar.add_event(
            Event(
                self.id,
                self.way.id,
                self.lane.id,
                self.way_percentage,
                self.speed,
            )
        )
