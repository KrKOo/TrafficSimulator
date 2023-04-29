from entities import Way, Crossroad
import matplotlib


def plot_lanes(plt: matplotlib.pyplot, way: Way):
    for forward_lane in way.lanes.forward:
        x = [node.lng for node in forward_lane.nodes]
        y = [node.lat for node in forward_lane.nodes]

        plt.plot(x, y, "g", linestyle="-", linewidth=1)
        # plt.plot(x[-1], y[-1], "bo")

    for backward_lane in way.lanes.backward:
        x = [node.lng for node in backward_lane.nodes]
        y = [node.lat for node in backward_lane.nodes]

        plt.plot(x, y, "r", linestyle="-", linewidth=1)
        # plt.plot(x[0], y[0], "bo")


def plot_ways(plt: matplotlib.pyplot, ways: list[Way]):
    for way in ways:
        plot_lanes(plt, way)


def plot_crossroads(plt: matplotlib.pyplot, crossroads: list[Crossroad]):
    for crossroad in crossroads:
        if crossroad.has_traffic_light:
            plt.plot(crossroad.node.pos.lng, crossroad.node.pos.lat, "go")
        else:
            plt.plot(crossroad.node.pos.lng, crossroad.node.pos.lat, "bo")
        # plt.annotate(
        #     f"{crossroad.id}",
        #     (crossroad.node.pos.lng, crossroad.node.pos.lat),
        # )
