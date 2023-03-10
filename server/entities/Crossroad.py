from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from entities import Way

import math
from .Node import Node
from .Lane import Lane


class NextOption:
    def __init__(self, way: Way, lanes: List[Lane]):
        self.way = way
        self.lanes = lanes


class CrossroadTurn:
    def __init__(self, through: Way, left: Way, right: Way):
        self.through = through
        self.left = left
        self.right = right


class Crossroad:
    def __init__(self, id: int, node: Node, ways: List[Way] = None):
        self.id = id
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

    # TODO: add lane parameter or something... idk
    def get_next_options(self, way: Way) -> List[NextOption]:
        next_options: List[NextOption] = []

        in_ways = [w for w in self._ways if w.nodes[-1].id == self.node.id]
        out_ways = [w for w in self._ways if w.nodes[0].id == self.node.id]

        for next_way in self._ways:
            if next_way == way:
                continue

            lanes = []
            if way in in_ways:
                if next_way in in_ways:
                    lanes = next_way.lanes.backward
                if next_way in out_ways:
                    lanes = next_way.lanes.forward
            else:
                if next_way in in_ways:
                    lanes = next_way.lanes.backward
                if next_way in out_ways:
                    lanes = next_way.lanes.forward

            next_options.append(NextOption(next_way, lanes))

        return next_options

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
