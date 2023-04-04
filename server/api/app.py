from flask import Flask, Response
import simpy
import random
from modules import Parser
from entities import Calendar, Car


app = Flask(__name__)


@app.route("/")
def hello_world():
    random.seed(0)
    env = simpy.Environment()
    parser = Parser(env)

    parser.apply_file("data/clean_lipuvka.osm")
    parser.init_crossroads()

    print("Roadnet parsed.")
    calendar = Calendar(env)

    for i in range(100):
        speed = random.randint(10, 60)
        Car(env, calendar, parser.ways[i], 0, speed)
    print("Cars spawned.")

    print("Simulating...")
    env.run(until=50000)
    print("Done.")

    response = Response(parser.pack() + calendar.pack())
    response.headers["Access-Control-Allow-Origin"] = "*"

    return response
