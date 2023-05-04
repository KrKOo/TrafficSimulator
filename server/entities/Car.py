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
from utils.globals import MIN_GAP, CROSSROAD_BLOCKING_TIME


class CarState(Enum):
    Undefinded = 0
    Crossing = 1
    Queued = 2
    Waiting = 3
    Despawning = 4


class Direction(Enum):
    Right = 1
    Left = 2


class Car(SimulationEntity, metaclass=WithId):
    def __init__(
        self,
        env: simpy.Environment,
        spawner: "VehicleSpawner",
        calendar: Calendar,
        way: Way,
        lane: Lane,
        position: float,
        speed: int,
        length: int = 0.003,
    ):
        SimulationEntity.__init__(self, env)
        self.id = next(self._ids)
        self.spawner = spawner
        self.calendar = calendar
        self._way = way
        self.lane = lane
        self.desired_speed = speed  # in km/h
        self._speed = speed  # in km/h
        self.length = length  # in km
        self._position = position  # in km
        self.update_time = self.env.now  # in seconds
        self.state = CarState.Crossing

        self.place_car_on_lane(lane, position)

        self._next_way = None
        self._next_lane = None
        self._lane_to_switch = None

        next_path = self._get_next_path()
        self._next_way, self._next_lane, self._lane_to_switch = (
            next_path if next_path else (None, None, None)
        )

        self._crossroad_blockers: list[list[simpy.Resource]] = []
        self._blocker_requests: list[list[simpy.Request]] = []
        self._next_crossroad_blocked = False
        self._crossroad_unblock_proc = None

        self.update_event = env.event()
        self.environment_update_event = env.event()

        self.controller_proc = env.process(self.controller())

        self.calendar_car_update()

    def __repr__(self):
        return str(self.id)
        # return (
        #     f"Car id: {self.id} way: {self.way.id if self.way else None}, lane: {self.lane.id if self.lane else None}, position: {self.position}, speed: {self.speed}, "
        #     f"state: {self.state}, next_way: {self._next_way.id if self._next_way else None}, next_lane: {self._next_lane.id if self._next_lane else None}, "
        #     f"car_ahead: {self.car_ahead.id if self.car_ahead else None}, car_behind: {self.car_behind.id if self.car_behind else None}"
        # )

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

        # release blockers if the way between crossroads was too short to do it regularly
        # self.env.process(self.unblock_all_crossroads_but_one())

    def unblock_all_crossroads_but_one(self):
        while len(self._crossroad_blockers) > 1:
            yield self.env.process(self._unblock_crossroad())

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
    def speed(self, value: int):
        self.position = self.position
        self._speed = value
        self.calendar_car_update()

        self.trigger_update_event()

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
    def lane_percentage(self) -> float:
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

    def place_car_on_lane(self, lane: Lane, position: float):
        self.lane = lane

        car_behind = lane.get_car_behind_position(position)
        if car_behind is None:
            self.lane.put(self)
        else:
            self.lane.put_ahead_of_car(self, car_behind)

        self.position = position

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

    def _release_blockers(self):
        while len(self._crossroad_blockers) > 0:
            yield self.env.process(self._unblock_crossroad())

        yield self.env.timeout(0)

    def _wait_and_block_crossroad(self):
        while self.is_next_crossroad_blocked:
            yield self.env.timeout(1)  # wait and try again

        print(f"Car {self.id} not waiting for timeout")
        yield self._block_next_crossroad()  # should be instant

    def despawn(self):
        self.speed = 0
        self.env.process(self._release_blockers())
        car_behind = self.car_behind
        self.lane.remove(self)
        self.poke_car_behind(car_behind)
        self.spawner.despawn(self)
        print(f"Car {self.id} despawned, {[car.id for car in self.lane.queue]}")

    def trigger_update_event(self):
        self.update_event.succeed()
        self.update_event = self.env.event()

    def trigger_environment_update_event(self):
        self.environment_update_event.succeed()
        self.environment_update_event = self.env.event()

    def poke_car_behind(self, car_to_poke):
        if car_to_poke:
            print(f"Car {self.id} poked car {car_to_poke.id} at {self.env.now}")
            car_to_poke.trigger_environment_update_event()

    @property
    def _car_ahead_update_event(self):
        return self.car_ahead.update_event if self.car_ahead else self.env.event()

    def get_mirror_position_in_lane(self, lane: Lane):
        return self.lane_percentage / 100 * lane.length

    def get_lane_direction(self, from_lane: Lane, to_lane: Lane):
        right_lane = from_lane.right
        while right_lane is not None:
            if right_lane == to_lane:
                return Direction.Right
            right_lane = right_lane.right

        left_lane = from_lane.left
        while left_lane is not None:
            if left_lane == to_lane:
                return Direction.Left
            left_lane = left_lane.left

        return None

    def get_lane_blocking_car(self, lane: Lane):
        mirror_position = self.get_mirror_position_in_lane(lane)
        car_ahead = lane.get_car_ahead_of_position(mirror_position)

        if (
            car_ahead
            and car_ahead.position - car_ahead.length - MIN_GAP < mirror_position
        ):
            return car_ahead

        car_behind = lane.get_car_behind_position(mirror_position)
        if car_behind and car_behind.position > mirror_position - self.length - MIN_GAP:
            return car_behind

        return None

    """
    ################################################
                    DRIVING MODEL
    ################################################
    """

    def get_behind_car_in_other_lane(self, lane: Lane, car: "Car"):
        remaining_distance = self.lane.length - self.position

        end_distance = min(0.01, remaining_distance * 0.5)

        end_position = self.position + end_distance
        end_position_in_dest_lane = (end_position / self.lane.length) * lane.length

        t_car_at_overtake_position = car.time_to_be_at_position(
            end_position_in_dest_lane + MIN_GAP + car.length + 0.005
        )

        new_speed = end_distance / (t_car_at_overtake_position / 3600)

        self.speed = math.floor(new_speed)
        get_behind_timeout = self.env.timeout(self.time_to_be_at_position(end_position))

        yield get_behind_timeout | car.update_event | self.environment_update_event

        if not get_behind_timeout.processed:
            return False

        return True

    def switch_closer_to_lane_process(self, to_lane: Lane):
        direction = self.get_lane_direction(self.lane, to_lane)
        if direction is None:
            return self.lane

        destination_lane = (
            self.lane.right if direction == Direction.Right else self.lane.left
        )

        can_switch = False

        while not can_switch:
            blocking_car = self.get_lane_blocking_car(destination_lane)

            if blocking_car:
                if blocking_car.speed == 0:
                    yield blocking_car.update_event
                    continue

                p_result = yield self.env.process(
                    self.get_behind_car_in_other_lane(destination_lane, blocking_car)
                )
                can_switch = p_result
            else:
                can_switch = True

        position_in_dest_lane = self.get_mirror_position_in_lane(destination_lane)
        car_behind = self.car_behind

        self.calendar_car_update()
        self.lane.remove(self)
        self.poke_car_behind(car_behind)
        self.place_car_on_lane(destination_lane, position_in_dest_lane)
        self.calendar_car_update()
        self.poke_car_behind(self.car_behind)

    def drive_to_lane_percentage(self, lane_percentage: float):
        lane_position = lane_percentage / 100 * self.lane.length

        if lane_position < self.position:
            return CarState.Undefinded

        if self.time_to_reach_car_ahead < 0:
            print("colision")
            return CarState.Despawning

        arrive_timeout = self.env.timeout(self.time_to_be_at_position(lane_position))
        catch_up_car_ahead_timeout = self.env.timeout(self.time_to_reach_car_ahead)

        yield arrive_timeout | catch_up_car_ahead_timeout | self.environment_update_event | self._car_ahead_update_event

        self.position = self.position

        if arrive_timeout.processed:
            return CarState.Undefinded

        if catch_up_car_ahead_timeout.processed:
            return CarState.Queued

        return CarState.Crossing

    def crossing_process(self):
        self.speed = self.desired_speed

        p = yield self.env.process(self.drive_to_lane_percentage(50))

        if CarState(p.value) != CarState.Undefinded:
            return p.value

        if self._lane_to_switch is not None:
            yield self.env.process(
                self.switch_closer_to_lane_process(self._lane_to_switch)
            )

            if self.lane == self._lane_to_switch:
                self._lane_to_switch = None

            return CarState.Crossing

        crossroad_blocking_position = self.lane.length - self.speed * (
            CROSSROAD_BLOCKING_TIME / 3600
        )
        crossroad_blocing_percentage = (
            crossroad_blocking_position / self.lane.length * 100
        )

        p = yield self.env.process(
            self.drive_to_lane_percentage(crossroad_blocing_percentage)
        )

        if CarState(p.value) != CarState.Undefinded:
            return p.value

        if not self.is_next_crossroad_blocked and self.is_first_in_lane:
            print(f"Car {self.id} blocking near crossroad at {self.env.now}")
            yield self.env.process(self._release_blockers())
            yield self._block_next_crossroad()  # should be instant
            self._next_crossroad_blocked = True
            print(f"Car {self.id} blocked near crossroad at {self.env.now}")

        p = yield self.env.process(self.drive_to_lane_percentage(100))
        if CarState(p.value) != CarState.Undefinded:
            return p.value

        return CarState.Waiting

    def queued_process(self):
        if not self.car_ahead:
            return CarState.Crossing

        self.speed = min(self.car_ahead.speed, self.desired_speed)

        yield self.environment_update_event | self._car_ahead_update_event
        if self.car_ahead:  # TODO: check if it is the same car ahead
            print(
                f"Car ahead {self.car_ahead.id} updated, {[car.id for car in self.lane.queue]}"
            )
            return CarState.Queued  # just update the speed
        else:
            return CarState.Crossing  # leave the queue

    def waiting_process(self):
        self.speed = 0
        if self._next_lane is None:
            return CarState.Despawning

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

        next_path = self._get_next_path()
        self._next_way, self._next_lane, self._lane_to_switch = (
            next_path if next_path else (None, None, None)
        )

        return CarState.Crossing

    def drive(self):
        while True:
            if self.state == CarState.Crossing:
                p = yield self.env.process(self.crossing_process())
            elif self.state == CarState.Queued:
                p = yield self.env.process(self.queued_process())
            elif self.state == CarState.Waiting:
                p = yield self.env.process(self.waiting_process())
            else:
                return

            self.state = CarState(p)

    def _get_next_path(self) -> tuple[Way, Lane, Turn]:
        crossroad = self.next_crossroad

        next_way_options = crossroad.get_next_way_options(self.way)
        lane_to_switch = None

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
            lane_options = crossroad.get_next_lane_options(self.way, next_way)
            if self.lane not in lane_options.keys():
                lane_to_switch = random.choice(list(lane_options.keys()))
                next_lane = random.choice(lane_options[lane_to_switch])

                self._lane_to_switch = lane_to_switch
            else:
                next_lane = random.choice(lane_options[self.lane])

        return next_way, next_lane, lane_to_switch

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
            f"Car {self.id} updated at {self.env.now}, position {self.position}, lane_percentage {self.lane_percentage} ,speed {self.speed}, state {self.state.name}, way {self.way.id}/{self.way.osm_id}, lane {self.lane.id}, car ahead {(self.car_ahead.id, self.car_ahead.lane_percentage) if self.car_ahead else None}, car behind {(self.car_behind.id, self.car_behind.lane_percentage) if self.car_behind else None}"
        )
        self.calendar.add_event(
            Event(
                self.id,
                self.way.id,
                self.lane.id,
                self.lane_percentage,
                self.speed,
            )
        )
