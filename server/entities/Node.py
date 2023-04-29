from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities import Way

import struct
from utils import LatLng

from utils.map_geometry import angle_between_nodes
from utils.math import get_point_from_angle_and_distance, haversine

LANE_GAP = 0.00003
CROSSROAD_OFFSET = 0.00004


class Node:
    def __init__(
        self,
        id: int,
        pos: LatLng,
        has_traffic_light: bool = False,
        ways: list["Way"] = None,
    ):
        self.id = id
        self.pos = pos
        self.has_traffic_light = has_traffic_light
        self._ways: list["Way"] = [] if ways is None else ways
        self.lane_nodes: dict[int, list[LatLng]] = []

    @property
    def ways(self):
        return self._ways

    def add_way(self, way: "Way"):
        self._ways.append(way)
        self.calculate_lane_nodes()

    def remove_way(self, way: "Way"):
        self._ways.remove(way)
        self.calculate_lane_nodes()

    def pack(self):
        return struct.pack("!Qff", self.id, self.pos.lat, self.pos.lng)

    def calculate_lane_nodes(self):
        self.lane_nodes = {}

        if len(self.ways) == 0:
            return
        else:
            for way in self.ways:
                way_lane_nodes = []
                node_idx = way.nodes.index(self)
                node_center = self.pos

                offset = min((way.length * 0.4) / 100, CROSSROAD_OFFSET)

                if node_idx == 0 or node_idx == len(way.nodes) - 1:
                    next_node = way.nodes[1] if node_idx == 0 else way.nodes[-2]

                    max_lanes = max([way.lane_count for way in self.ways])
                    offset = min((way.length * 0.4) / 100, max_lanes * LANE_GAP * 0.6)

                    way_angle = angle_between_nodes(self, next_node)
                    node_center = get_point_from_angle_and_distance(
                        self.pos, way_angle, offset
                    )

                    if node_idx == 0:
                        angle = way_angle + 90
                    else:
                        angle = way_angle - 90

                else:
                    angle1 = angle_between_nodes(
                        way.nodes[node_idx], way.nodes[node_idx - 1]
                    )
                    angle2 = angle_between_nodes(
                        way.nodes[node_idx], way.nodes[node_idx + 1]
                    )
                    angle = (angle1 + angle2) / 2

                    if angle < angle2:
                        angle = angle + 180

                angle = angle % 360

                way_width = (way.lane_count - 1) * LANE_GAP

                base_lane_pos = get_point_from_angle_and_distance(
                    node_center, angle, -way_width / 2
                )

                for i in range(way.lane_count):
                    lane_node = get_point_from_angle_and_distance(
                        base_lane_pos, angle, i * LANE_GAP
                    )

                    way_lane_nodes.append(lane_node)

                self.lane_nodes[way.id] = way_lane_nodes
