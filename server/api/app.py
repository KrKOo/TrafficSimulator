from flask import Flask, Response, request
import simpy
import random
from modules import Parser, VehicleSpawner
from entities import Calendar

app = Flask(__name__)


@app.route("/")
def hello_world():
    vehicle_count = request.args.get("vehicle_count", default=100, type=int)
    time_span = request.args.get("time_span", default=100, type=int)
    simulation_seed = request.args.get("seed", default=0, type=int)

    random.seed(simulation_seed)
    env = simpy.Environment()
    parser = Parser(env)

    parser.parse("data/clean_brno.osm")

    print("Roadnet parsed.")
    calendar = Calendar(env)
    spawner = VehicleSpawner(env, calendar, parser.ways)

    print("Spawning vehicles...")
    spawner.spawn(vehicle_count)

    print("Simulating...")

    env.run(until=time_span)

    for vehicle in spawner.vehicles:
        vehicle.calendar_car_update()

    print("Simulation finished.")

    response = Response(parser.pack() + calendar.pack())
    response.headers["Access-Control-Allow-Origin"] = "*"

    return response
