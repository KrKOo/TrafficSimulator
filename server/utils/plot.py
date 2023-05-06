from entities import Way, Crossroad, Lane
import matplotlib


def plot_way(plt: matplotlib.pyplot, way: Way):
    for forward_lane in way.lanes.forward:
        plot_lane(plt, forward_lane, "g")

    for backward_lane in way.lanes.backward:
        plot_lane(plt, backward_lane, "r")


def plot_lane(plt: matplotlib.pyplot, lane: Lane, color: str = "g"):
    x = [node.lng for node in lane.nodes]
    y = [node.lat for node in lane.nodes]

    plt.plot(x, y, color, linestyle="-", linewidth=1)


def plot_ways(plt: matplotlib.pyplot, ways: list[Way]):
    for way in ways:
        plot_way(plt, way)


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

        for lane in crossroad.lanes:
            plot_lane(plt, lane, "b")
