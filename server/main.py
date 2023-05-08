from matplotlib import pyplot as plt
import simpy

from modules import Parser, VehicleSpawner
from entities import Car, Calendar
from utils import plot

from api.app import app

if __name__ == "__main__":
    app.run()

    # env = simpy.Environment()

    # parser = Parser(env)

    # parser.parse("data/clean_brno.osm")
    # calendar = Calendar(env)
    # spawner = VehicleSpawner(env, calendar, parser.ways)

    # print("Spawning vehicles...")
    # spawner.spawn_multiple(1000)

    # print("Simulating...")

    # env.run(until=1000)

    # for vehicle in spawner.vehicles:
    #     vehicle.calendar_car_update()

    # plt.axes().set_aspect("equal", "box")
    # plot.plot_ways(plt, parser.ways)
    # plot.plot_crossroads(plt, parser.crossroads)
    # plt.show()
