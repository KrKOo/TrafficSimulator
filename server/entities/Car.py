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
from .CarEvent import CarEvent
from .Calendar import Calendar
from .Lane import Lane
from .Crossroad import Crossroad, BlockableLane
from utils import LatLng, Direction
from utils.map_geometry import is_incoming_way
from utils.math import haversine
from utils.globals import MIN_GAP, CROSSROAD_BLOCKING_TIME


class CarState(Enum):
    Undefinded = 0
    Crossing = 1
    CrossingCrossroad = 2
    Queued = 3
    Waiting = 4
    Despawning = 5


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
        # current way
        self._way = way
        # current lane
        self.lane = lane
        # max comfortable speed for the driver
        self.desired_speed = speed  # in km/h
        self._speed = speed  # in km/h
        # car length
        self.length = length  # in km
        self._position = position  # in km
        self.update_time = self.env.now  # in seconds
        self.state = CarState.Crossing

        self.place_car_on_lane(lane, position)

        self._next_way = None
        self._next_lanes: list[Lane] = []
        self._lane_to_switch = None

        next_path = self._get_next_path()
        self._next_way, self._next_lanes, self._lane_to_switch = (
            next_path if next_path else (None, [], None)
        )

        self._blocked_crossroad_lanes: list[BlockableLane] = []
        self._lane_block_requests: list[simpy.Request] = []

        self._next_crossroad_blocked = False
        self._crossroad_unblock_proc = None

        # event called by the current car on its state change
        self.update_event = env.event()
        # event called by other cars to notify this car about their state change
        self.environment_update_event = env.event()
        self.controller_proc = env.process(self.controller())
        # insert the initial state to the calendar
        self.calendar_car_update()

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

        self._trigger_update_event()

        if len(self._blocked_crossroad_lanes) > 1 or (
            not self._next_crossroad_blocked and len(self._blocked_crossroad_lanes) == 1
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
                    self.env, self._unblock_crossroad_process(), time_to_leave_crossroad
                )

    def _unblock_crossroad_process(self):
        self._unblock_crossroad()
        yield self.env.timeout(0)

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
        """Returns the car ahead of this car in the same lane"""
        if not self.is_first_in_lane:
            queue_position = self.lane.get_car_position(self)
            return self.lane.queue[queue_position + 1]
        return None

    @property
    def car_ahead_multiple_lanes(self) -> "Car":
        """Returns the car ahead of this car in the same lane or in the next lane"""
        if not self.is_first_in_lane:
            queue_position = self.lane.get_car_position(self)
            return self.lane.queue[queue_position + 1]
        else:
            car_in_next_lane = (
                self._next_lanes[0].last
                if len(self._next_lanes) > 0
                and self._next_lanes[0].way != self.lane.way
                else None
            )

            if car_in_next_lane is None:
                car_in_next_next_lane = (
                    self._next_lanes[1].last
                    if len(self._next_lanes) > 1
                    and self._next_lanes[1].way != self.lane.way
                    else None
                )

            res = car_in_next_lane or car_in_next_next_lane

            return res if res is not None and res.car_ahead != self else None

    @property
    def car_behind(self) -> "Car":
        """Returns the car behind this car in the same lane"""
        if not self.is_last_in_lane:
            queue_position = self.lane.get_car_position(self)
            return self.lane.queue[queue_position - 1]

    @property
    def lane_end_time(self) -> float:
        """Returns the time it takes to reach the end of the la"""
        if self.speed == 0:
            return math.inf

        end_time = (self.lane.length - self.position) / self.speed
        return end_time * 3600

    @property
    def lane_leave_time(self) -> float:
        """Returns the time it takes to leave the lane (with the rear of the car + MIN_GAP)"""
        if self.speed == 0:
            return math.inf

        leave_time = (
            self.lane.length - self.position + self.length + MIN_GAP
        ) / self.speed
        return leave_time

    @property
    def distance_to_car_ahead(self) -> float:
        """Returns the distance to the car ahead of this car in the same lane"""
        car_ahead = self.car_ahead

        if car_ahead is None:
            return None

        if car_ahead.lane == self.lane:
            return car_ahead.position - self.position - (car_ahead.length + MIN_GAP)
        else:
            return (
                (self.lane.length - self.position)
                + car_ahead.position
                - (car_ahead.length + MIN_GAP)
            )

    @property
    def time_to_reach_car_ahead(self) -> float:
        """Returns the time it takes to reach the car ahead of this car in the same lane"""
        distance = self.distance_to_car_ahead

        if distance is None:  # no car ahead
            return math.inf

        if self.speed <= self.car_ahead.speed:
            return math.inf

        return (distance / (self.speed - self.car_ahead_multiple_lanes.speed)) * 3600

    @property
    def next_crossroad(self) -> Crossroad:
        """Returns the next crossroad the car will reach"""
        if self.way is None:
            return self.lane.crossroad

        return (
            self.way.next_crossroad if self.lane.is_forward else self.way.prev_crossroad
        )

    def time_to_travel_distance(self, distance: float) -> float:
        """Returns the time it takes to travel the given distance"""
        if self.speed == 0:
            return math.inf

        return (distance / self.speed) * 3600

    def time_to_be_at_position(self, dest_position: float) -> float:
        """
        Returns the time it takes to be at the given position.
        Returns negative time if the car is already past the dest_position
        """
        return self.time_to_travel_distance(dest_position - self.position)

    @property
    def has_car_on_right(self):
        """Returns True if there is a car on the right hand side on the next crossroad"""
        right_way = self.next_crossroad.turns[self.way].right
        if right_way is None:
            return False

        right_lanes = (
            right_way.lanes.forward
            if is_incoming_way(self.next_crossroad.node, right_way)
            else right_way.lanes.backward
        )

        for lane in right_lanes:
            first_car = lane.first

            if (
                first_car is not None
                and first_car.time_to_be_at_position(lane.length)
                < self.time_to_be_at_position(self.lane.length)
                + CROSSROAD_BLOCKING_TIME
            ):
                print(
                    f"Car {self.id} has car {first_car.id} on right at {self.env.now}"
                )
                return True

        return False

    @property
    def driving_on_main_way(self):
        """Returns True if the car is currently on the main way and the next way is also a main way"""
        if (
            self.way in self.next_crossroad.main_ways
            and self._next_way in self.next_crossroad.main_ways
        ):
            return True

    @property
    def next_way_lane(self) -> Lane:
        """Returns the next lane the car will be on"""
        return [
            next_lane for next_lane in self._next_lanes if next_lane.way is not None
        ][0]

    @property
    def is_next_crossroad_blocked(self) -> bool:
        """Returns True if the next crossroad is blocked"""
        if self._next_way is None:
            return False

        lane_to_cross = self.next_crossroad.get_lane(self.lane, self.next_way_lane)
        if lane_to_cross and lane_to_cross.disabled:
            return True

        lanes = self.next_crossroad.get_conflicting_lanes(
            (self.way, self.lane), (self._next_way, self.next_way_lane)
        )

        next_crossroad_blocker_request = (
            self._lane_block_requests[-1] if len(self._lane_block_requests) > 0 else []
        )

        for lane in lanes:
            if (
                lane.blocker.count > 0
                and lane.users[0] != next_crossroad_blocker_request
            ):
                return True

        return False

    def place_car_on_lane(self, lane: Lane, position: float):
        """Places the car on the given lane at the given position"""
        self.lane = lane
        self.position = position

        car_behind = lane.get_car_behind_position(position)
        if car_behind is None:
            self.lane.put(self)
        else:
            if car_behind._next_crossroad_blocked:
                car_behind._release_blockers()

            self.lane.put_ahead_of_car(self, car_behind)
            car_behind.trigger_environment_update_event()

    def _block_next_crossroad(self):
        """Blocks the next crossroad"""
        self._release_blockers()

        if self._next_way is None:
            return self.env.timeout(0)

        lane = self.next_crossroad.get_lane(self.lane, self.next_way_lane)
        if lane is None:
            return self.env.timeout(0)

        self._blocked_crossroad_lanes.append(lane)

        blocker_request = lane.request()

        self._lane_block_requests.append(blocker_request)

        return blocker_request

    def _unblock_crossroad(self):
        """Unblocks the next crossroad"""
        if len(self._blocked_crossroad_lanes) == 0:
            self._crossroad_unblock_proc = None
            return

        lane = self._blocked_crossroad_lanes.pop(0)
        lane_request = self._lane_block_requests.pop(0)

        lane.release(lane_request)

        self._crossroad_unblock_proc = None
        print(f"Car {self.id} Crossroad unblocked at {self.env.now}, {lane.id}")

    def _release_blockers(self):
        """Releases all lane blockers"""
        while len(self._blocked_crossroad_lanes) > 0:
            self._unblock_crossroad()

    def _wait_and_block_crossroad(self):
        """Waits for the next crossroad to be unblocked and then blocks it"""
        while self.is_next_crossroad_blocked:
            yield self.env.timeout(1)  # wait and try again

        print(f"Car {self.id} not waiting for timeout")
        yield self._block_next_crossroad()  # should be instant

    def despawn(self):
        self.speed = 0
        self._release_blockers()
        car_behind = self.car_behind
        self.lane.remove(self)
        self.poke_car_behind(car_behind)
        self.spawner.despawn(self)
        print(f"Car {self.id} despawned, {[car.id for car in self.lane.queue]}")

    def _trigger_update_event(self):
        self.update_event.succeed()
        self.update_event = self.env.event()

    def trigger_environment_update_event(self):
        self.environment_update_event.succeed()
        self.environment_update_event = self.env.event()

    def poke_car_behind(self, car_to_poke):
        """Triggers the enironment update event of the car behind this car"""
        if car_to_poke:
            print(f"Car {self.id} poked car {car_to_poke.id} at {self.env.now}")
            car_to_poke.trigger_environment_update_event()

    @property
    def _car_ahead_update_event(self):
        return self.car_ahead.update_event if self.car_ahead else self.env.event()

    def get_mirror_position_in_lane(self, lane: Lane):
        """Returns the mirrored position on the given lane"""
        return self.lane_percentage / 100 * lane.length

    def get_lane_direction(self, from_lane: Lane, to_lane: Lane):
        """Returns the direction from the from_lane to the to_lane"""
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
        """Returns the car blocking the given lane"""
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
        """Slow down to get behind a car in another lane"""
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
        print(
            f"Car {self.id} is slowing down to {self.speed} to get behind car {car.id}"
        )
        yield get_behind_timeout | car.update_event | self.environment_update_event

        if not get_behind_timeout.processed:
            return False

        return True

    def switch_closer_to_lane_process(self, to_lane: Lane):
        """Switches to the lane closer to the given lane, or to the given lane itself"""
        direction = self.get_lane_direction(self.lane, to_lane)
        if direction is None:
            return CarState.Crossing

        destination_lane = (
            self.lane.right if direction == Direction.Right else self.lane.left
        )

        can_switch = False

        while not can_switch:
            blocking_car = self.get_lane_blocking_car(destination_lane)

            if blocking_car:
                if blocking_car.speed == 0:
                    if blocking_car.state != CarState.Queued:
                        return CarState.Despawning
                    self.speed = 0
                    yield blocking_car.update_event & self.env.timeout(1)
                    self.speed = min(self.desired_speed, self.way.max_speed)
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

        return CarState.Crossing

    def drive_to_lane_percentage(self, lane_percentage: float):
        """Drives the car to the given lane percentage"""
        print(f"Car {self.id} driving to {lane_percentage}%")
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
        """Drives the car to the end of the lane and switches to the next lane if needed"""
        if self.lane.crossroad is not None:
            print(f"Car {self.id} lane crossroad {self.lane.crossroad.id}")
            return CarState.CrossingCrossroad

        self.speed = min(self.desired_speed, self.way.max_speed)

        p = yield self.env.process(
            self.drive_to_lane_percentage(random.randint(30, 80))
        )
        print(
            f"Car {self.id} is at {self.lane_percentage}% of way {self.way.osm_id} at {self.env.now}"
        )

        if CarState(p.value) != CarState.Undefinded:
            return p.value

        if self._lane_to_switch is not None:
            print(
                f"Car {self.id} is switching lane at {self.lane_percentage}% of way {self.way.osm_id} at {self.env.now}"
            )
            p = yield self.env.process(
                self.switch_closer_to_lane_process(self._lane_to_switch)
            )

            if CarState(p.value) != CarState.Crossing:
                return CarState(p.value)

            print(
                f"Car {self.id} switched lane at {self.lane_percentage}% of way {self.way.osm_id} at {self.env.now}"
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

        print(
            f"Car {self.id} is driving to {crossroad_blocing_percentage}% at {self.env.now}"
        )
        p = yield self.env.process(
            self.drive_to_lane_percentage(crossroad_blocing_percentage)
        )
        print(
            f"Car {self.id} is at {self.lane_percentage}% of way {self.way.osm_id} at {self.env.now}"
        )

        if CarState(p.value) != CarState.Undefinded:
            return p.value

        # Block the next crossroad if needed and possible
        if (
            not self.is_next_crossroad_blocked
            and self.is_first_in_lane
            and (self.driving_on_main_way or not self.has_car_on_right)
        ):
            print(
                f"Car {self.id} blocking near crossroad {self.way.next_crossroad.id if self.lane.is_forward else self.way.prev_crossroad.id}, way: {self.way.id} at {self.env.now}"
            )
            yield self._block_next_crossroad()  # should be instant
            self._next_crossroad_blocked = True
            print(
                f"Car {self.id} blocked near crossroad {self.way.next_crossroad.id if self.lane.is_forward else self.way.prev_crossroad.id} at {self.env.now}"
            )

        p = yield self.env.process(self.drive_to_lane_percentage(100))
        if CarState(p.value) != CarState.Undefinded:
            return p.value

        return CarState.Waiting

    def queued_process(self):
        """Drives behind the car ahead, tries to switch lane"""
        if not self.car_ahead:
            return CarState.Crossing

        # Switch lane if would switch anyways at some point
        if self._lane_to_switch is not None:
            yield self.env.process(
                self.switch_closer_to_lane_process(self._lane_to_switch)
            )

            if self.lane == self._lane_to_switch:
                self._lane_to_switch = None

            return CarState.Crossing

        self.speed = min(self.car_ahead.speed, self.desired_speed)
        original_car_ahead = self.car_ahead
        lane_end_timeout = self.env.timeout(
            self.time_to_be_at_position(self.lane.length)
        )
        yield self.environment_update_event | self._car_ahead_update_event | lane_end_timeout

        if lane_end_timeout.processed:
            return CarState.Waiting

        if self.is_first_in_lane:
            car_ahead = self.car_ahead_multiple_lanes
            self.speed = (
                car_ahead.speed
                if car_ahead and car_ahead.position <= car_ahead.length + MIN_GAP
                else self.desired_speed  # TODO: Careful
            )
            if self.speed == 0:
                self.speed = self.desired_speed

            yield self.env.timeout(self.time_to_be_at_position(self.lane.length))
            return CarState.Waiting

        print(f"Car {self.id} queue {[car.id for car in self.lane.queue]}")
        if self.car_ahead and self.car_ahead == original_car_ahead:
            print(
                f"Car ahead {self.car_ahead.id} updated, {[car.id for car in self.lane.queue]}"
            )
            return CarState.Queued  # just update the speed
        else:
            return CarState.Crossing  # leave the queue

    def crossroad_crossing_process(self):
        """Drives through the crossroad"""
        self.calendar_car_update()

        p = yield self.env.process(self.drive_to_lane_percentage(100))

        if CarState(p.value) != CarState.Undefinded:
            if CarState(p.value) == CarState.Crossing:
                return CarState.CrossingCrossroad

            return CarState(p.value)

        self.calendar_car_update()
        car_behind_in_prev_lane = self.car_behind

        self.lane.pop(self)
        self.lane = self._next_lanes.pop(0)
        self.way = self.lane.way
        self.lane.put(self)

        self.position = 0

        self.poke_car_behind(car_behind_in_prev_lane)

        next_path = self._get_next_path()
        self._next_way, self._next_lanes, self._lane_to_switch = (
            next_path if next_path else (None, [], None)
        )

        return CarState.Crossing

    def waiting_process(self):
        """Waiting at the crossroad"""
        prev_speed = self.speed
        self.speed = 0
        if len(self._next_lanes) == 0:
            return CarState.Despawning

        if not self._next_crossroad_blocked and self.way is not None:
            print(
                f"Car {self.id} blocking crossroad {self.next_crossroad.id} at {self.env.now}"
            )
            # wait on the crossroad if other cars are blocking it
            yield self.env.process(self._wait_and_block_crossroad())
            print(
                f"Car {self.id} blocked crossroad {self.next_crossroad.id} at {self.env.now}"
            )

        yield self.env.timeout(0.001)
        car_behind_in_prev_lane = self.car_behind

        if not self.is_first_in_lane:
            return CarState.Despawning

        self.lane.pop(self)
        self.lane = self._next_lanes.pop(0)
        self.way = self.lane.way
        self.lane.put(self)

        self.position = 0

        self.poke_car_behind(car_behind_in_prev_lane)

        if self.way is None:
            self.speed = prev_speed
            return CarState.CrossingCrossroad
        else:
            print(
                f"Car {self.id} switched way to {self.way.id}/{self.way.osm_id} at {self.env.now}"
            )
            next_path = self._get_next_path()
            (
                self._next_way,
                self._next_lanes,
                self._lane_to_switch,
            ) = (
                next_path if next_path else (None, [], None)
            )
            return CarState.Crossing

    def drive(self):
        """Main car process"""
        while True:
            if self.state == CarState.Crossing:
                p = yield self.env.process(self.crossing_process())
            elif self.state == CarState.CrossingCrossroad:
                p = yield self.env.process(self.crossroad_crossing_process())
            elif self.state == CarState.Queued:
                p = yield self.env.process(self.queued_process())
            elif self.state == CarState.Waiting:
                p = yield self.env.process(self.waiting_process())
            else:
                return

            self.state = CarState(p)

    def _get_next_path(self) -> tuple[Way, list[Lane], Lane]:
        """Returns a random next path to drive"""
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

        crossroad_lane = crossroad.get_lane(
            self._lane_to_switch or self.lane, next_lane
        )

        next_lanes = []
        if crossroad_lane:
            next_lanes.append(crossroad_lane)
        next_lanes.append(next_lane)
        return next_way, next_lanes, lane_to_switch

    def get_coords(self):
        """Returns the coordinates of the car"""
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
            f"Car {self.id} updated at {self.env.now}, position {self.position}, lane_percentage {self.lane_percentage} ,speed {self.speed}, state {self.state.name}, way {(self.way.id, self.way.osm_id) if self.way else None}, lane {self.lane.id}, queue: {[car.id for car in self.lane.queue]}, car ahead {(self.car_ahead.id, self.car_ahead.lane_percentage) if self.car_ahead else None}, car behind {(self.car_behind.id, self.car_behind.lane_percentage) if self.car_behind else None}"
        )
        self.calendar.add_car_event(
            CarEvent(
                self.id,
                self.way.id if self.way else None,
                self.next_crossroad.id if self.way is None else None,
                self.lane.id,
                self.lane_percentage,
                self.speed,
            )
        )
