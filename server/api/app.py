from flask import Flask, Response
import simpy
import random
from modules import Parser, VehicleSpawner
from entities import Calendar, Car
from utils import plot
import matplotlib.pyplot as plt


app = Flask(__name__)


@app.route("/")
def hello_world():
    random.seed(0)
    env = simpy.Environment()
    parser = Parser(env)

    parser.parse("data/clean_brno.osm")

    print("Roadnet parsed.")
    calendar = Calendar(env)
    spawner = VehicleSpawner(env, calendar, parser.ways)

    print("Spawning vehicles...")
    spawner.spawn(1000)

    print("Simulating...")

    env.run(until=500)

    for vehicle in spawner.vehicles:
        vehicle.calendar_car_update()

    print("Simulation finished.")

    response = Response(parser.pack() + calendar.pack())
    response.headers["Access-Control-Allow-Origin"] = "*"

    return response
