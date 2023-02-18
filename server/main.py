import osmium
from matplotlib import pyplot as plt
import numpy as np


class LatLng:
    def __init__(self, lat: float, lng: float):
        self.lat = lat
        self.lng = lng


class Road:
    def __init__(self, start: LatLng, end: LatLng, max_speed: int, lane_count: int):
        self.start = start
        self.end = end
        self.max_speed = max_speed
        self.lane_count = lane_count


class Parser(osmium.SimpleHandler):
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self._nodes = []
        self.lines = []

    def node(self, n: osmium.osm.Node):
        self._nodes.append([n.id, LatLng(n.location.lat, n.location.lon)])

    def way(self, w: osmium.osm.Way):
        node_dict = dict(self._nodes)

        lines_nodes = [
            [w.nodes[i].ref, w.nodes[i + 1].ref] for i in range(len(w.nodes) - 1)
        ]

        for line_nodes in lines_nodes:
            if line_nodes[0] in node_dict.keys() and line_nodes[1] in node_dict.keys():
                self.lines.append(
                    Road(
                        node_dict[line_nodes[0]],
                        node_dict[line_nodes[1]],
                        w.tags.get("maxspeed"),
                        w.tags.get("lanes") or 1,
                    )
                )


if __name__ == "__main__":
    parser = Parser()

    parser.apply_file("data/clean_palackeho.xml")

    for line in parser.lines:
        x = [line.start.lng, line.end.lng]
        y = [line.start.lat, line.end.lat]
        plt.plot(x, y, "ro", linestyle="-")

        plt.text(
            (x[0] + x[1]) / 2,
            (y[0] + y[1]) / 2,
            line.lane_count,
            fontsize=10,
            ha="center",
            va="center",
        )

    plt.show()
