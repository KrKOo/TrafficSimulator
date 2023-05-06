from matplotlib import pyplot as plt
import simpy
import random
import json

from modules import Parser
from entities import Car, Calendar
from utils import plot

from api.app import app

if __name__ == "__main__":
    app.run()

    # env = simpy.Environment()

    # parser = Parser(env)

    # parser.parse("data/clean_lipuvka.osm")

    # plt.axes().set_aspect("equal", "box")
    # plot.plot_ways(plt, parser.ways)
    # plot.plot_crossroads(plt, parser.crossroads)
    # plt.show()
