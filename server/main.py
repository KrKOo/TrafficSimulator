import osmium
from matplotlib import pyplot as plt
import numpy as np
import simpy

from utils import LatLng
from entities import Road


class Parser(osmium.SimpleHandler):
    def __init__(self, env):
        osmium.SimpleHandler.__init__(self)
        self.env = env
        self._nodes = []
        self.roads = []

    def node(self, n: osmium.osm.Node):
        self._nodes.append([n.id, LatLng(n.location.lat, n.location.lon)])

    def way(self, w: osmium.osm.Way):
        node_dict = dict(self._nodes)

        lines_nodes = [
            [w.nodes[i].ref, w.nodes[i + 1].ref] for i in range(len(w.nodes) - 1)
        ]

        for idx, line_nodes in enumerate(lines_nodes):
            if line_nodes[0] in node_dict.keys() and line_nodes[1] in node_dict.keys():
                try:
                    maxspeed = int(w.tags.get("maxspeed", "50"))
                except ValueError:
                    maxspeed = 50

                try:
                    lanes = int(w.tags.get("lanes", "0"))
                except ValueError:
                    lanes = 0

                self.roads.append(
                    Road(
                        idx,
                        env,
                        node_dict[line_nodes[0]],
                        node_dict[line_nodes[1]],
                        maxspeed,
                        lanes,
                        w.tags.get("oneway") == "yes",
                    )
                )


if __name__ == "__main__":
    env = simpy.Environment()

    parser = Parser(env)

    parser.apply_file("data/clean_moravak.osm")

    for road in parser.roads:
        x = [road.start.lng, road.end.lng]
        y = [road.start.lat, road.end.lat]
        if road.oneway:
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
            plt.plot(x, y, "ro", linestyle="-", linewidth=2)

        plt.text(
            (x[0] + x[1]) / 2,
            (y[0] + y[1]) / 2,
            road.lane_count,
            fontsize=10,
            ha="center",
            va="center",
        )

    plt.show()
