import simpy

from matplotlib import pyplot as plt
from utils import plot, LatLng, HighwayClass

from entities import Car, Way, WayLanesProps, Node, Crossroad, Calendar
import random


def get_roadnet(env: simpy.Environment):
    n1 = Node(1, LatLng(49.0, 16.1))
    n2 = Node(2, LatLng(49.05, 16.1))
    n3 = Node(3, LatLng(49.1, 16.1))
    n4 = Node(4, LatLng(49.1, 16.0))
    n5 = Node(5, LatLng(49.05, 16.0))
    n6 = Node(6, LatLng(49.0, 16.0))

    c1 = Crossroad(env, n5)
    c2 = Crossroad(env, n2)

    w1 = Way(50, HighwayClass.primary, WayLanesProps(1, 1), [n5, n6, n1, n2])
    w1.prev_crossroad = c1
    w1.next_crossroad = c2

    w2 = Way(50, HighwayClass.primary, WayLanesProps(1, 1), [n2, n3, n4, n5])
    w2.prev_crossroad = c2
    w2.next_crossroad = c1

    w3 = Way(50, HighwayClass.primary, WayLanesProps(1, 0), [n2, n5])
    w3.prev_crossroad = c2
    w3.next_crossroad = c1

    return ([w1, w2, w3], [c1, c2])


if __name__ == "__main__":
    env = simpy.Environment()
    ways, crossroads = get_roadnet(env)
    calendar = Calendar(env)

    car1 = Car(env, calendar, ways[0], 0, 50)
    car2 = Car(env, calendar, ways[1], 0, 10)
    car2 = Car(env, calendar, ways[2], 0, 30)

    env.run(until=100000)

    plot.plot_ways(plt, ways)
    plot.plot_crossroads(plt, crossroads)
    plt.show()
