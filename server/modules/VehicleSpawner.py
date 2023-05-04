import random
from entities.Car import Car


class VehicleSpawner:
    def __init__(self, env, calendar, ways):
        self.env = env
        self.calendar = calendar
        self.ways = ways
        self.vehicles: list[Car] = []

    def spawn_multiple(self, amount):
        for _ in range(amount):
            self.spawn()

    def despawn(self, vehicle):
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)

        new_vehicle = self.spawn()
        print(f"New vehicle {new_vehicle.id} spawned")

    def spawn(self):
        speed = random.randint(10, 50)
        way = self.ways[random.randint(0, len(self.ways) - 1)]
        lane = way.lanes[random.randint(0, len(way.lanes) - 1)]
        position = random.uniform(lane.length * 0.2, lane.length * 0.8)
        vehicle = Car(self.env, self, self.calendar, way, lane, position, speed)
        self.vehicles.append(vehicle)
        return vehicle
