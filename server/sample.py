import simpy

from matplotlib import pyplot as plt
from utils import plot

from entities import Car, Way, WayLanesProps, Node, Crossroad
from utils import LatLng


def get_ways():
    n1 = Node(1, LatLng(49.0, 16.1))
    n2 = Node(2, LatLng(49.1, 16.1))
    n3 = Node(3, LatLng(49.1, 16.0))
    n4 = Node(4, LatLng(49.0, 16.0))

    c1 = Crossroad(0, n1)
    c2 = Crossroad(1, n2)
    c3 = Crossroad(2, n3)
    c4 = Crossroad(3, n4)

    w1 = Way(0, 50, WayLanesProps(1, 1, [], []), [n1, n2])
    w1.prev_crossroad = c1
    w1.next_crossroad = c2
    w2 = Way(1, 50, WayLanesProps(1, 1, [], []), [n2, n3])
    w2.prev_crossroad = c2
    w2.next_crossroad = c3
    w3 = Way(2, 50, WayLanesProps(1, 1, [], []), [n3, n4])
    w3.prev_crossroad = c3
    w3.next_crossroad = c4
    w4 = Way(3, 50, WayLanesProps(1, 1, [], []), [n4, n1])
    w4.prev_crossroad = c4
    w4.next_crossroad = c1

    w5 = Way(4, 50, WayLanesProps(1, 1, [], []), [n2, n4])
    w5.prev_crossroad = c2
    w5.next_crossroad = c4

    return [w1, w2, w3, w4, w5]

if __name__ == "__main__":
    env = simpy.Environment()
    ways = get_ways()

    car1 = Car(env, ways[0], 1, 50)
    # car2 = Car(env, ways[1], 0, 10)
    # car3 = Car(env, roads[2], 0, 31)
    env.run(until=100000)
    plot.plot_ways(plt, ways)
