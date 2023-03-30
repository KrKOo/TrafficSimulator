from entities import Way, Crossroad
import matplotlib


def plot_ways(plt: matplotlib.pyplot, ways: list[Way]):
    for way in ways:
        for idx, road in enumerate(way.roads):
            x = [road.start.lng, road.end.lng]
            y = [road.start.lat, road.end.lat]

            if len(way.lanes.backward) == 0:  # oneway
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

            if idx == len(way.roads) // 2:
                plt.text(
                    (x[0] + x[1]) / 2,
                    (y[0] + y[1]) / 2,
                    f"{way.id}",
                    fontsize=10,
                    ha="center",
                    va="center",
                )


def plot_crossroads(plt: matplotlib.pyplot, crossroads: list[Crossroad]):
    for crossroad in crossroads:
        plt.plot(crossroad.node.pos.lng, crossroad.node.pos.lat, "bo")
        plt.annotate(
            f"{crossroad.id}",
            (crossroad.node.pos.lng, crossroad.node.pos.lat),
        )
