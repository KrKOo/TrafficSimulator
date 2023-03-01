import simpy

from matplotlib import pyplot as plt
from utils import plot

from entities import Car, Road, RoadLanes, Lane
from utils import LatLng


def get_roads():
    r4 = Road(
        3,
        LatLng(49.1, 16.0),
        LatLng(49.0, 16.0),
        50,
        RoadLanes(forward=[Lane()], backward=[Lane()]),
    )
    r3 = Road(
        2,
        LatLng(49.1, 16.1),
        LatLng(49.1, 16.0),
        50,
        RoadLanes(forward=[Lane()], backward=[Lane()]),
        next_road=r4,
    )
    r2 = Road(
        1,
        LatLng(49.0, 16.1),
        LatLng(49.1, 16.1),
        50,
        RoadLanes(forward=[Lane()], backward=[Lane()]),
        next_road=r3,
    )
    r1 = Road(
        0,
        LatLng(49.0, 16.0),
        LatLng(49.0, 16.1),
        50,
        RoadLanes(forward=[Lane()], backward=[Lane()]),
        next_road=r2,
    )

    r4.set_next_road(r1)

    return [r1, r2, r3, r4]


if __name__ == "__main__":
    env = simpy.Environment()
    roads = get_roads()

    car1 = Car(env, roads[0], 1, 50)
    car2 = Car(env, roads[1], 0, 10)
    # car3 = Car(env, roads[2], 0, 31)
    env.run(until=100000)
    plot.plot_roads(plt, roads)
