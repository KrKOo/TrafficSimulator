from utils import Turn, HighwayClass
import struct
from .Node import Node
from .Road import Road
from .Lane import Lane
from .Crossroad import Crossroad
from .Entity import EntityBase, WithId
from utils.math import haversine
from utils.types import LatLng
from utils.helpers import transpose

LANE_GAP = 0.003
CROSSROAD_OFFSET = 0.005


class WayLanesProps:
    def __init__(
        self,
        forward_count: int,
        backward_count: int,
        turn_lanes_forward: list[list[Turn]] = None,
        turn_lanes_backward: list[list[Turn]] = None,
    ):
        self.forward_lane_count = forward_count
        self.backward_lane_count = backward_count
        self.forward_lane_turn = turn_lanes_forward
        self.backward_lane_turn = turn_lanes_backward


class WayLanes:
    def __init__(self, forward: list[Lane], backward: list[Lane]):
        self.forward = forward
        self.backward = backward

        for lane in self.forward:
            lane.is_forward = True

        for lane in self.backward:
            lane.is_forward = False

    def __len__(self):
        return len(self.forward) + len(self.backward)

    def __getitem__(self, index):
        lanes = self.forward + self.backward
        return lanes[index]


class Way(EntityBase, metaclass=WithId):
    def __init__(
        self,
        max_speed: int,
        highway_class: HighwayClass,
        lanes_props: WayLanesProps,
        nodes: list[Node] = None,
        osm_id: int = None,
    ):
        super().__init__()
        self.id = next(self._ids)
        self.osm_id = osm_id
        self.highway_class = highway_class
        self.max_speed = max_speed
        self.lane_props = lanes_props
        self.lanes: WayLanes = None
        self._nodes = []
        self._next_crossroad: Crossroad = None
        self._prev_crossroad: Crossroad = None

        self.length = None
        self.nodes = nodes if nodes is not None else []

        self.roads = self._init_roads()

    def _get_length(self):
        length = 0
        for i in range(len(self.nodes) - 1):
            length += haversine(self.nodes[i].pos, self.nodes[i + 1].pos)

        return length

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, nodes: list[Node]):
        for node in self._nodes:
            if self in node.ways:
                node.remove_way(self)

        self._nodes = nodes
        self.length = self._get_length()

        for node in self._nodes:
            if self not in node.ways:
                node.add_way(self)

        self.lanes = self._init_lanes()

        if self.next_crossroad:
            self.next_crossroad.update()
        if self.prev_crossroad:
            self.prev_crossroad.update()

    @property
    def lane_count(self):
        return self.lane_props.forward_lane_count + self.lane_props.backward_lane_count

    def pack(self):
        packed_lanes = [lane.pack() for lane in self.lanes]
        way_struct = struct.Struct(f"!III")

        return way_struct.pack(self.id, self.max_speed, len(packed_lanes)) + b"".join(
            packed_lanes
        )

    def _get_lanes_nodes(self):
        lanes_nodes = [[] for _ in self.nodes]

        for idx, way_node in enumerate(self.nodes):
            for lane_nodes in way_node.lane_nodes[self.id]:
                lanes_nodes[idx].append(lane_nodes)

        return transpose(lanes_nodes)

    def _init_lanes(self) -> WayLanes:
        lanes_nodes = self._get_lanes_nodes()

        forward_lanes = []
        backward_lanes = []

        for i in range(self.lane_props.forward_lane_count):
            turns = (
                self.lane_props.forward_lane_turn[i]
                if self.lane_props.forward_lane_turn
                and i < len(self.lane_props.forward_lane_turn)
                else None
            )
            forward_lanes.append(Lane(lanes_nodes[i], self, None, True, turns=turns))

        for i in range(len(forward_lanes)):
            forward_lanes[i].left = (
                forward_lanes[i + 1] if i + 1 < len(forward_lanes) else None
            )
            forward_lanes[i].right = forward_lanes[i - 1] if i - 1 >= 0 else None

        lanes_nodes.reverse()
        for i in range(self.lane_props.backward_lane_count):
            turns = (
                self.lane_props.backward_lane_turn[i]
                if self.lane_props.backward_lane_turn
                and i < len(self.lane_props.backward_lane_turn)
                else None
            )
            backward_lanes.append(Lane(lanes_nodes[i], self, None, False, turns=turns))

        for i in range(len(backward_lanes)):
            backward_lanes[i].left = (
                backward_lanes[i + 1] if i + 1 < len(backward_lanes) else None
            )
            backward_lanes[i].right = backward_lanes[i - 1] if i - 1 >= 0 else None

        return WayLanes(forward_lanes, backward_lanes)

    def _init_roads(self) -> list[Road]:
        lines = [
            [self.nodes[i].pos, self.nodes[i + 1].pos]
            for i in range(len(self.nodes) - 1)
        ]

        roads = [Road(line[0], line[1]) for line in lines]  # TODO: fix ID

        for i in range(len(roads) - 1):
            roads[i].set_next_road(roads[i + 1])

        return roads

    # splits way at given node, the beginning remains in the original way, the end is returned as a new way
    def split(self, node: Node):
        node_index = None

        for i, n in enumerate(self.nodes):  # TODO: refactor
            if n.id == node.id:
                node_index = i
                break

        new_way_nodes = self.nodes[: node_index + 1]
        this_way_nodes = self.nodes[node_index:]

        self.roads = self.roads[node_index:]
        self.nodes = this_way_nodes

        new_way_lane_props = WayLanesProps(
            self.lane_props.forward_lane_count,
            self.lane_props.backward_lane_count,
        )

        new_way = Way(
            self.max_speed,
            self.highway_class,
            new_way_lane_props,
            new_way_nodes,
            self.osm_id,
        )

        new_way.prev_crossroad = self.prev_crossroad
        self.prev_crossroad = None
        self.next_crossroad = self.next_crossroad  # in case the way is a loop

        return new_way

    def remove_short_segments(self):
        self.nodes = self._get_nodes_without_short_segments(self.nodes)

    def _get_nodes_without_short_segments(self, nodes: list[Node]):
        if len(nodes) < 3:
            return nodes

        start_segments_length = 0
        start_segments_node_count = 0

        end_segments_length = 0
        end_segments_node_count = 0

        res_nodes = []

        start_max_lanes = max(
            [len(lane_nodes) for lane_nodes in self.nodes[0].lane_nodes.values()]
        )
        start_offset = start_max_lanes * LANE_GAP / 2
        for idx in range(len(nodes) - 1):
            start_segments_length += haversine(nodes[idx].pos, nodes[idx + 1].pos)
            start_segments_node_count = idx + 1
            if start_segments_length >= start_offset:
                break

        end_max_lanes = max(
            [len(lane_nodes) for lane_nodes in self.nodes[-1].lane_nodes.values()]
        )
        end_offset = end_max_lanes * LANE_GAP / 2
        for idx in range(len(nodes) - 1):
            end_segments_length += haversine(nodes[-idx - 1].pos, nodes[-idx - 2].pos)
            end_segments_node_count = idx + 1
            if end_segments_length >= end_offset:
                break

        if start_segments_node_count + end_segments_node_count >= len(nodes):
            res_nodes = [nodes[0], nodes[-1]]
        else:
            res_nodes = (
                [nodes[0]]
                + nodes[start_segments_node_count:-end_segments_node_count]
                + [nodes[-1]]
            )

        return res_nodes

    @property
    def next_crossroad(self) -> Crossroad:
        return self._next_crossroad

    @property
    def prev_crossroad(self) -> Crossroad:
        return self._prev_crossroad

    @next_crossroad.setter
    def next_crossroad(self, crossroad: Crossroad):
        if crossroad is None:
            if self._next_crossroad is None:
                return
            self._next_crossroad.remove_way(self)
            self._next_crossroad = None
            return

        self._next_crossroad = crossroad
        if self not in self._next_crossroad.ways:
            self._next_crossroad.add_way(self)

    @prev_crossroad.setter
    def prev_crossroad(self, crossroad: Crossroad):
        if crossroad is None:
            if self._prev_crossroad is None:
                return
            self._prev_crossroad.remove_way(self)
            self._prev_crossroad = None
            return

        self._prev_crossroad = crossroad
        if self not in self._prev_crossroad.ways:
            self._prev_crossroad.add_way(self)
