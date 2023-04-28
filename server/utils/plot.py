from entities import Way, Crossroad
import matplotlib


def plot_ways(plt: matplotlib.pyplot, ways: list[Way]):
    for way in ways:
        for node_idx, node in enumerate(way.nodes):
            for lane_idx, lane_node in enumerate(node.lane_nodes[way.id]):
                plt.plot(lane_node.lng, lane_node.lat, "go")

                if node_idx != len(way.nodes) - 1:
                    next_node = way.nodes[node_idx + 1]
                    if lane_idx < len(next_node.lane_nodes[way.id]):
                        x = [lane_node.lng, next_node.lane_nodes[way.id][lane_idx].lng]
                        y = [lane_node.lat, next_node.lane_nodes[way.id][lane_idx].lat]

                        if lane_idx >= way.lane_props.forward_lane_count:
                            x[1], x[0] = x[0], x[1]
                            y[1], y[0] = y[0], y[1]

                        plt.annotate(
                            "",
                            xy=([x[1], y[1]]),
                            xytext=([x[0], y[0]]),
                            arrowprops={
                                "arrowstyle": "->",
                                "linestyle": "-",
                                "linewidth": 1,
                                "shrinkA": 0,
                                "shrinkB": 0,
                                "color": "green",
                            },
                        )

        # for idx, road in enumerate(way.roads):
        #     x = [road.start.lng, road.end.lng]
        #     y = [road.start.lat, road.end.lat]

        #     if len(way.lanes.backward) == 0:  # oneway
        #         plt.annotate(
        #             "",
        #             xy=([x[1], y[1]]),
        #             xytext=([x[0], y[0]]),
        #             arrowprops={
        #                 "arrowstyle": "->",
        #                 "linestyle": "-",
        #                 "linewidth": 2,
        #                 "shrinkA": 0,
        #                 "shrinkB": 0,
        #                 "color": "green",
        #             },
        #         )
        #     else:
        #         plt.plot(x, y, "g", linestyle="-", linewidth=2)

        # if idx == len(way.roads) // 2:
        #     plt.text(
        #         (x[0] + x[1]) / 2,
        #         (y[0] + y[1]) / 2,
        #         f"{way.id}",
        #         fontsize=10,
        #         ha="center",
        #         va="center",
        #     )


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
