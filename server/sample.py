import simpy

from matplotlib import pyplot as plt
from utils import plot

from entities import Car
from utils import Road, LatLng

def get_roads(env: simpy.Environment):
    r4 = Road(env, LatLng(49.1, 16.0), LatLng(49.0, 16.0), 50, 2)
    r3 = Road(env, LatLng(49.1, 16.1), LatLng(49.1, 16.0), 50, 2, next_road=r4)
    r2 = Road(env, LatLng(49.0, 16.1), LatLng(49.1, 16.1), 50, 2, next_road=r3)
    r1 = Road(env, LatLng(49.0, 16.0), LatLng(49.0, 16.1), 50, 2, next_road=r2)

    r4.set_next_road(r1)

    return [r1, r2, r3, r4]

if __name__ == "__main__":
    env = simpy.Environment()
    roads = get_roads(env)
    # plot.plot_roads(plt, roads)

    car1 = Car(1, env, roads[0], 0, 50)
    car2 = Car(2, env, roads[1], 0, 11)
    env.run(until=100000)


