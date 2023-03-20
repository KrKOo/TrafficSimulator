from matplotlib import pyplot as plt
import simpy
import random

from modules import Parser
from entities import Car, Calendar
from utils import plot

from api.app import app

if __name__ == "__main__":
    random.seed(0)

    app.run()

    # env = simpy.Environment()

    # parser = Parser(env)

    # parser.apply_file("data/clean_brno.osm")
    # parser.init_crossroads()


    # calendar = Calendar(env)

    # for i in range(1000):
    #     Car(env, calendar, parser.ways[i%100], 0, 30)

    # env.run(until=50000)

    # with open("out.sim", "wb") as outfile:
    #     outfile.write(calendar.pack())

    # plot.plot_ways(plt, parser.ways)
    # plot.plot_crossroads(plt, parser.crossroads)
    # plt.show()
