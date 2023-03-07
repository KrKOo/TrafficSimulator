from typing import List
from utils import LatLng, Turn
import copy
from .Node import Node
from .Road import Road
from .Lane import Lane
from .Crossroad import Crossroad


class WayLanesProps:
    def __init__(
        self,
        forward_count: int,
        backward_count: int,
        turn_lanes_forward: List[List[Turn]] = None,
        turn_lanes_backward: List[List[Turn]] = None,
    ):
        self.forward_lane_count = forward_count
        self.backward_lane_count = backward_count
        self.forward_lane_turn = turn_lanes_forward
        self.backward_lane_turn = turn_lanes_backward
        # TODO: railway, psv, vehicle lanes


class WayLanes:
    def __init__(self, forward: List[Lane], backward: List[Lane]):
        self.forward = forward
        self.backward = backward

        for lane in self.forward:
            lane.is_forward = True

        for lane in self.backward:
            lane.is_forward = False

    def __getitem__(self, index):
        lanes = self.forward + self.backward
        return lanes[index]


class Way:
    def __init__(
        self, id: int, max_speed: int, lanes_props: WayLanesProps, nodes: List[Node]
    ):
        self.id = id
        self.max_speed = max_speed
        self.lane_props = lanes_props
        self.lanes = self._init_lanes(lanes_props)
        self.nodes = nodes

        self.roads = self._init_roads()

        self._next_crossroad: Crossroad = None
        self._prev_crossroad: Crossroad = None

    @property
    def length(self):
        return sum([road.length for road in self.roads])

    def _init_lanes(self, lanes_props) -> WayLanes:
        if lanes_props.forward_lane_turn is None:
            forward_lanes = [Lane(True) for _ in range(lanes_props.forward_lane_count)]
        else:
            forward_lanes = [
                Lane(True, turn=lane_turn)
                for lane_turn in lanes_props.forward_lane_turn
            ]

        if lanes_props.backward_lane_turn is None:
            backward_lanes = [
                Lane(False) for _ in range(lanes_props.backward_lane_count)
            ]
        else:
            backward_lanes = [
                Lane(False, turn=lane_turn)
                for lane_turn in lanes_props.backward_lane_turn
            ]

        return WayLanes(forward_lanes, backward_lanes)

    def _init_roads(self) -> List[Road]:
        lines = [
            [self.nodes[i].pos, self.nodes[i + 1].pos]
            for i in range(len(self.nodes) - 1)
        ]

        roads = [Road(1, line[0], line[1]) for line in lines]  # TODO: fix ID

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
            2 * self.id, self.max_speed, new_way_lane_props, new_way_nodes
        )  # TODO: fix ID

        new_way.prev_crossroad = self.prev_crossroad
        self.prev_crossroad = None

        return new_way

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
            self._next_crossroad.ways.remove(self)
            self._next_crossroad = None
            return

        self._next_crossroad = crossroad
        if self not in self._next_crossroad.ways:
            self._next_crossroad.ways.append(
                self
            )  # TODO: check if it's not already there

    @prev_crossroad.setter
    def prev_crossroad(self, crossroad: Crossroad):
        if crossroad is None:
            if self._prev_crossroad is None:
                return
            self._prev_crossroad.ways.remove(self)
            self._prev_crossroad = None
            return

        self._prev_crossroad = crossroad
        if self not in self._prev_crossroad.ways:
            self._prev_crossroad.ways.append(
                self
            )  # TODO: check if it's not already there
