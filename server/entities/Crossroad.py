from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from entities import Way

import math
from .Node import Node
from .Lane import Lane
from utils import Turn
from .Entity import EntityBase, WithId


class NextWayOption:
    def __init__(self, way: Way, turn: Turn = Turn.none):
        self.way = way
        self.turn = turn


class CrossroadTurn:
    def __init__(self, through: Way, left: Way, right: Way):
        self.through = through
        self.left = left
        self.right = right


class Crossroad(EntityBase, metaclass=WithId):
    def __init__(self, node: Node, ways: List[Way] = None):
        super().__init__()
        self.id = next(self._ids)
        self._ways = ways if ways is not None else []
        self.node = node
        self.turns: Dict[int, CrossroadTurn] = {}

    def __repr__(self):
        way_turns = {}
        for way_id, turns in self.turns.items():
            way_turns[way_id] = [
                turns.through.id if turns.through else None,
                turns.left.id if turns.left else None,
                turns.right.id if turns.right else None,
            ]

        text = (
            f"Crossroad {self.id}:\n"
            f"Ways: {[way.id for way in  self._ways]}\n"
            f"Turns: {way_turns}"
        )
        return text

    @property
    def ways(self) -> List[Way]:
        return self._ways

    def add_way(self, way: Way):
        self._ways.append(way)
        self._update_turns()

    def remove_way(self, way: Way):
        self._ways.remove(way)

    def get_next_way_options(self, way: Way) -> List[NextWayOption]:
        next_way_options: List[NextWayOption] = []

        for next_way in self._ways:
            if next_way == way:
                continue

            turn_direction = self._get_way_turn(way, next_way)

            if self._is_in_way(next_way):
                if len(next_way.lanes.backward) > 0:
                    next_way_options.append(NextWayOption(next_way, turn_direction))
            else:
                if len(next_way.lanes.forward) > 0:
                    next_way_options.append(NextWayOption(next_way, turn_direction))

        return next_way_options

    def get_next_lane_options(
        self, from_way: Way, to_way: Way
    ) -> Dict[Lane, List[Lane]]:
        turn_direction = self._get_way_turn(from_way, to_way)

        in_lanes = (
            from_way.lanes.forward
            if self._is_in_way(from_way)
            else from_way.lanes.backward
        )
        out_lanes = (
            to_way.lanes.backward if self._is_in_way(to_way) else to_way.lanes.forward
        )

        lane_options: Dict[Lane, List[Lane]] = {}

        for lane in in_lanes:
            if lane.turns == None or Turn.none in lane.turns:
                lane_options[lane] = out_lanes
            else:
                lane_options[lane] = [
                    out_lane for out_lane in out_lanes if turn_direction in lane.turns
                ]

        return lane_options

    def _is_in_way(self, way: Way) -> bool:
        if way.nodes[-1].id == self.node.id:
            return True
        elif way.nodes[0].id == self.node.id:
            return False

        assert True, f"Way {way.id} is not connected to crossroad {self.id}"

    def _get_way_turn(self, from_way: Way, to_way: Way):
        way_turns = self.turns[from_way.id]

        if way_turns.through == to_way:
            return Turn.through
        elif way_turns.left == to_way:
            return Turn.left
        elif way_turns.right == to_way:
            return Turn.right

        return None

    def _get_way_angles(self) -> Dict[Way, float]:
        in_ways = [w.id for w in self._ways if w.nodes[-1].id == self.node.id]
        out_ways = [w.id for w in self._ways if w.nodes[0].id == self.node.id]

        way_angle: Dict[Way, float] = {}

        for way in self._ways:
            delta_lat, delta_lng = 0, 0

            if way.id in in_ways:
                delta_lng = way.nodes[-2].pos.lng - self.node.pos.lng
                delta_lat = way.nodes[-2].pos.lat - self.node.pos.lat
            elif way.id in out_ways:
                delta_lng = way.nodes[1].pos.lng - self.node.pos.lng
                delta_lat = way.nodes[1].pos.lat - self.node.pos.lat

            angle = math.atan2(delta_lat, delta_lng)
            angle = (angle * 180 / math.pi) % 360

            way_angle[way] = angle

        return way_angle

    # TODO: what if there are more ways to the same direction?
    def _update_turns(self):
        way_angle = self._get_way_angles()

        for way in self._ways:
            this_way_angle = way_angle[way]

            turns = CrossroadTurn(None, None, None)

            for target_way, angle in way_angle.items():
                delta_angle = (angle - this_way_angle) % 360

                if 45 <= delta_angle < 135:
                    turns.right = target_way
                elif 135 <= delta_angle < 225:
                    turns.through = target_way
                elif 225 <= delta_angle <= 315:
                    turns.left = target_way

                self.turns[way.id] = turns
