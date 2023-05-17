import random
from entities.Car import Car
from utils.globals import MIN_TRAVEL_DISTANCE, MAX_TRAVEL_DISTANCE


class VehicleSpawner:
    def __init__(self, env, calendar, ways):
        self.env = env
        self.calendar = calendar
        self.ways = ways
        self.vehicles: list[Car] = []

    def spawn_multiple(self, amount):
        for _ in range(amount):
            self.spawn_vehicle()

    def despawn(self, vehicle):
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)

        self.spawn_vehicle()

    def spawn_vehicle(self):
        speed = random.randint(70, 100)
        way = self.ways[random.randint(0, len(self.ways) - 1)]
        lane = way.lanes[random.randint(0, len(way.lanes) - 1)]
        position = random.uniform(lane.length * 0.2, lane.length * 0.8)
        car_length = random.uniform(0.002, 0.006)
        ways_to_cross_count = random.randint(MIN_TRAVEL_DISTANCE, MAX_TRAVEL_DISTANCE)

        vehicle = Car(
            self.env,
            self,
            self.calendar,
            way,
            lane,
            position,
            speed,
            car_length,
            ways_to_cross_count,
        )
        self.vehicles.append(vehicle)
        return vehicle
