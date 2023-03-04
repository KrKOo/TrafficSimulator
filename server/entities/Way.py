from typing import List
from utils import LatLng, Turn
from .Node import Node
from .Road import Road, RoadLanes
from .Lane import Lane
from .Crossroad import Crossroad

class WayLanes:
    def __init__(self, forward_count: int, backward_count: int, turn_lanes_forward: List[List[Turn]], turn_lanes_backward: List[List[Turn]]):
        self.forward_lane_count = forward_count
        self.backward_lane_count = backward_count
        self.forward_lane_turn = turn_lanes_forward
        self.backward_lane_turn = turn_lanes_backward
        # TODO: railway, psv, vehicle lanes

class Way:
    def __init__(self, id: int, max_speed: int, lanes: WayLanes, oneway: bool, nodes: List[Node]):
        self.id = id
        self.max_speed = max_speed
        self.lanes = lanes
        self.oneway = oneway
        self.nodes = nodes

        self.roads = self._init_roads()

        self.next_crossroad: Crossroad = None
        self.prev_crossroad: Crossroad = None

    def _init_roads(self) -> List[Road]:
        lines = [[self.nodes[i].pos, self.nodes[i + 1].pos] for i in range(len(self.nodes) - 1)]

        if len(self.lanes.forward_lane_turn) == 0:
            forward_lanes = [Lane(True) for _ in range(self.lanes.forward_lane_count)]
        else:
            forward_lanes = [Lane(True, turn=lane_turn) for lane_turn in self.lanes.forward_lane_turn]

        forward_lanes = self._init_next_lanes(forward_lanes, True)

        if len(self.lanes.backward_lane_turn) == 0:
            backward_lanes = [Lane(False) for _ in range(self.lanes.backward_lane_count)]
        else:
            backward_lanes = [Lane(False, turn=lane_turn) for lane_turn in self.lanes.backward_lane_turn]

        backward_lanes = self._init_next_lanes(backward_lanes, False)

        lanes = RoadLanes(forward_lanes, backward_lanes)

        roads = [Road(1, line[0], line[1], self.max_speed, lanes, self.oneway) for line in lines] #TODO: fix ID

        return roads

    def _init_next_lanes(self, lanes: List[Lane], forward: bool) -> List[Lane]:
        for idx, lane in enumerate(lanes):
            if idx == 0 or idx == len(lanes) - 1:
                continue

            lane.next = lanes[idx + 1] if forward else lanes[idx - 1]

        return lanes
