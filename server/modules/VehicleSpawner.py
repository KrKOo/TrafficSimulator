import random
from entities.Car import Car


class VehicleSpawner:
    def __init__(self, env, calendar, ways):
        self.env = env
        self.calendar = calendar
        self.ways = ways
        self.vehicles: list[Car] = []

    def spawn(self, amount):
        for i in range(amount):
            speed = random.randint(10, 50)
            vehicle = Car(self.env, self, self.calendar, self.ways[i], 0, speed)
            self.vehicles.append(vehicle)

    def despawn(self, vehicle):
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
        way = self.ways[random.randint(0, len(self.ways) - 1)]
        speed = random.randint(10, 50)
        new_vehicle = Car(self.env, self, self.calendar, way, 0, speed)
        print(f"New vehicle {new_vehicle.id} spawned")
