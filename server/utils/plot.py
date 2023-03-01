from typing import List
from entities import Road
import matplotlib


def plot_roads(plt: matplotlib.pyplot, roads: List[Road]):
    for road in roads:
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
            f"{len(road.lanes.forward)} + {len(road.lanes.backward)}",
            fontsize=10,
            ha="center",
            va="center",
        )

    plt.show()
