from matplotlib import pyplot as plt
import numpy as np
import simpy
from modules import Parser
from entities import Car


if __name__ == "__main__":
    env = simpy.Environment()

    parser = Parser(env)

    parser.apply_file("data/clean_lipuvka.osm")

    for idx, way in enumerate(parser.ways):
        roads = way.roads
        for road in roads:
            x = [road.start.lng, road.end.lng]
            y = [road.start.lat, road.end.lat]
            if len(way.lanes.backward) == 0: # oneway
                plt.annotate(
                    "",
                    xy=([x[1], y[1]]),
                    xytext=([x[0], y[0]]),
                    arrowprops={
                        "arrowstyle": "->",
                        "linestyle": "-",
                        "linewidth": 2,
                        "shrinkA": 0,
                        "shrinkB": 0,
                        "color": "red",
                    },
                )
            else:
                plt.plot(x, y, "r", linestyle="-", linewidth=2)

            fw_turns = [lane.turn for lane in way.lanes.forward if lane.turn is not None]
            bw_turns = [lane.turn for lane in way.lanes.backward if lane.turn is not None]

            plt.text(
                (x[0] + x[1]) / 2,
                (y[0] + y[1]) / 2,
                # f"{fw_turns}, {bw_turns}",
                f"{idx}, {way.id}",
                fontsize=10,
                ha="center",
                va="center",
            )

            plt.plot(way.prev_crossroad.node.pos.lng, way.prev_crossroad.node.pos.lat, 'go')
            plt.plot(way.next_crossroad.node.pos.lng, way.next_crossroad.node.pos.lat, 'go')

    plt.show()

    car1 = Car(env, parser.ways[13], 0, 50)
    env.run(until=100000)

