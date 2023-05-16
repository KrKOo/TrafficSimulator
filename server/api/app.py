from flask import Flask, Response, request
import simpy
import struct
import random
from modules import Parser, VehicleSpawner
from entities import Calendar

app = Flask(__name__)


@app.route("/")
def simulation():
    vehicle_count = request.args.get("vehicle_count", default=100, type=int)
    time_span = request.args.get("time_span", default=100, type=int)
    simulation_seed = request.args.get("seed", default=0, type=int)

    random.seed(simulation_seed)
    env = simpy.Environment()
    calendar = Calendar(env)

    parser = Parser(env, calendar)

    parser.parse("data/clean_brno.osm")

    print("Roadnet parsed.")
    spawner = VehicleSpawner(env, calendar, parser.ways)

    print("Spawning vehicles...")
    spawner.spawn_multiple(vehicle_count)

    print("Simulating...")

    env.run(until=time_span)

    for vehicle in spawner.vehicles:
        vehicle.calendar_car_update()

    print("Simulation finished.")

    roadnet_data = parser.pack()
    roadnet_bytes = roadnet_data[0]
    node_count, way_count, crossroad_count = roadnet_data[1]

    event_data = calendar.pack()
    event_bytes = event_data[0]
    car_event_count, crossroad_event_count = event_data[1]

    struct_header = struct.pack(
        "!IIIII",
        node_count,
        way_count,
        crossroad_count,
        car_event_count,
        crossroad_event_count,
    )

    response = Response(struct_header + roadnet_bytes + event_bytes)
    response.headers["Access-Control-Allow-Origin"] = "*"
    print(
        node_count, way_count, crossroad_count, car_event_count, crossroad_event_count
    )

    return response
