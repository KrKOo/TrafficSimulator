from matplotlib import pyplot as plt
import simpy
import random

from modules import Parser
from entities import Car
from utils import plot


if __name__ == "__main__":
    random.seed(0)
    env = simpy.Environment()

    parser = Parser(env)

    parser.apply_file("data/clean_brno.osm")
    parser.init_crossroads()

    car1 = Car(env, parser.ways[13], 0, 50)

    env.run(until=100000)

    plot.plot_ways(plt, parser.ways)
    plot.plot_crossroads(plt, parser.crossroads)
    plt.show()
