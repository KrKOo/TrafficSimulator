from enum import Enum
import simpy
from .Road import Road
from .Entity import SimulationEntity

MIN_GAP = 0.001


class CarState(Enum):
    Crossing = 1
    Queued = 2


class Car(SimulationEntity):
    def __init__(
        self,
        env: simpy.Environment,
        road: Road,
        lane_id: int,
        speed: int,
        length: int = 0.003,
    ):
        SimulationEntity.__init__(self, env)
        self.road = road
        self.lane = road.lanes[lane_id]
        self.desired_speed = speed  # in km/h
        self.speed = speed  # in km/h
        self.length = length  # in km
        self._position = 0  # in km
        self.update_time = 0  # in seconds
        self.state = CarState.Crossing
        self.lane.put(self)

        self.drive_proc = env.process(self.drive())

    @property
    def position(self):
        return self._position + self.speed * ((self.env.now - self.update_time) / 3600)

    @position.setter
    def position(self, value):
        self._position = value
        self.update_time = self.env.now

    def drive(self):
        while True:
            current_queue_position = self.lane.get_car_position(self)

            if self.state == CarState.Crossing:
                if current_queue_position < len(self.lane.queue) - 1:
                    car_ahead = self.lane.queue[current_queue_position - 1]
                    # TODO: Bad calculation of end times

                    # time for the car ahead to reach the end of the road
                    car_ahead_end_time = (
                        self.road.length - car_ahead.position + self.length
                    ) / car_ahead.speed
                    # time to reach the end of the road
                    end_time = (
                        self.road.length - self.position + self.length
                    ) / self.speed

                    if car_ahead_end_time > end_time:
                        # time to reach the car ahead
                        dt = (car_ahead.position - self.position - car_ahead.length) / (
                            self.speed - car_ahead.speed
                        )
                        yield self.env.timeout(dt * 3600)
                        print(
                            f"Car {self.id} reached the car ahead {car_ahead.id} at {self.env.now} seconds"
                        )
                        self.position = car_ahead.position - car_ahead.length
                        self.update_time = self.env.now
                        self.state = CarState.Queued
                        self.speed = car_ahead.speed

            elif self.state == CarState.Queued:
                if current_queue_position == len(self.lane.queue) - 1:
                    self.state = CarState.Crossing
                    self.speed = self.desired_speed

            time_to_end = (self.road.length - self.position) / self.speed
            yield self.env.timeout(time_to_end * 3600)
            print(
                f"Car {self.id} reached the end of the road at {self.env.now} seconds, road length: {self.road.length} km"
            )
            self.road = self.road.next_road
            self.lane = self.lane.next
            self.lane.put(self)
            self.position = 0
