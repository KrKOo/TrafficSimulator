from typing import List
from utils import LatLng, Turn
import copy
from .Node import Node
from .Road import Road
from .Lane import Lane
from .Crossroad import Crossroad

class WayLanesProps:
    def __init__(self, forward_count: int, backward_count: int, turn_lanes_forward: List[List[Turn]], turn_lanes_backward: List[List[Turn]]):
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
    def __init__(self, id: int, max_speed: int, lanes_props: WayLanesProps, nodes: List[Node]):
        self.id = id
        self.max_speed = max_speed
        self.lanes = self._init_lanes(lanes_props)
        self.nodes = nodes

        self.roads = self._init_roads()

        self._next_crossroad: Crossroad = None
        self._prev_crossroad: Crossroad = None

    @property
    def length(self):
        return sum([road.length for road in self.roads])

    def _init_lanes(self, lanes_props) -> WayLanes:
        if len(lanes_props.forward_lane_turn) == 0:
            forward_lanes = [Lane(True) for _ in range(lanes_props.forward_lane_count)]
        else:
            forward_lanes = [Lane(True, turn=lane_turn) for lane_turn in lanes_props.forward_lane_turn]

        if len(lanes_props.backward_lane_turn) == 0:
            backward_lanes = [Lane(False) for _ in range(lanes_props.backward_lane_count)]
        else:
            backward_lanes = [Lane(False, turn=lane_turn) for lane_turn in lanes_props.backward_lane_turn]

        return WayLanes(forward_lanes, backward_lanes)

    def _init_roads(self) -> List[Road]:
        lines = [[self.nodes[i].pos, self.nodes[i + 1].pos] for i in range(len(self.nodes) - 1)]

        roads = [Road(1, line[0], line[1]) for line in lines] #TODO: fix ID

        for i in range(len(roads) - 1):
            roads[i].set_next_road(roads[i + 1])

        return roads

    @property
    def next_crossroad(self) -> Crossroad:
        return self._next_crossroad

    @property
    def prev_crossroad(self) -> Crossroad:
        return self._prev_crossroad

    @next_crossroad.setter
    def next_crossroad(self, crossroad: Crossroad):
        self._next_crossroad = crossroad
        if self not in self._next_crossroad.ways:
            self._next_crossroad.ways.append(self) #TODO: check if it's not already there

    @prev_crossroad.setter
    def prev_crossroad(self, crossroad: Crossroad):
        self._prev_crossroad = crossroad
        if self not in self._prev_crossroad.ways:
            self._prev_crossroad.ways.append(self) #TODO: check if it's not already there

