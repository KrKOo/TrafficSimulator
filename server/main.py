from matplotlib import pyplot as plt
import simpy
import random
import json

from modules import Parser
from entities import Car, Calendar
from utils import plot

from api.app import app

if __name__ == "__main__":
    random.seed(0)

    # app.run()

    env = simpy.Environment()

    parser = Parser(env)

    parser.apply_file("data/clean_brno.pbf")
    parser.init_crossroads()
    calendar = Calendar(env)

    for i in range(100):
        speed = random.randint(10, 60)
        Car(env, calendar, parser.ways[i], 0, speed)

    env.run(until=100000)

    # with open("out.sim", "wb") as outfile:
    #     outfile.write(calendar.pack())

    # with open("out.json", "w") as outfile:
    #     outfile.write(json.dumps(calendar.get_data()))

    # plot.plot_ways(plt, parser.ways)
    # plot.plot_crossroads(plt, parser.crossroads)
    # plt.show()
