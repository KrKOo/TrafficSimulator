from flask import Flask, Response
import simpy
from modules import Parser
from entities import Calendar, Car


app = Flask(__name__)

@app.route("/")
def hello_world():
    print("Simulating...")
    env = simpy.Environment()
    parser = Parser(env)

    parser.apply_file("data/clean_brno.osm")
    parser.init_crossroads()

    calendar = Calendar(env)

    for i in range(1000):
        Car(env, calendar, parser.ways[i%100], 0, 30)

    env.run(until=50000)
    print("Done.")

    response = Response(calendar.pack())
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response

