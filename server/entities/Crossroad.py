from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities import Way

import math
import simpy
import collections
import struct

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

    def __repr__(self) -> str:
        return f"CrossroadTurn(through={self.through.id if self.through else None}, left={self.left.id if self.left else None}, right={self.right.id if self.right else None})"


class Crossroad(EntityBase, metaclass=WithId):
    def __init__(self, env: simpy.Environment, node: Node):
        super().__init__()
        self.id = next(self._ids)
        self.env = env
        self._ways: list[Way] = []
        self.node: Node = node
        self.turns: dict[int, CrossroadTurn] = {}
        self.blockers: collections.defaultdict[int, dict[int, simpy.Resource]] = {}

        self.main_ways: list[Way] = []

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

    def pack(self):
        crossroad_struct = struct.Struct("!IQ")
        return crossroad_struct.pack(self.id, self.node.id)

    @property
    def has_traffic_light(self):
        return self.node.has_traffic_light

    @property
    def ways(self) -> list[Way]:
        return self._ways

    def add_way(self, way: Way):
        self._ways.append(way)
        self._update_turns()
        self._update_main_ways()
        self._update_blockers()

    def remove_way(self, way: Way):
        self._ways.remove(way)
        self._update_turns()
        self._update_main_ways()
        self._update_blockers()

    def _update_blockers(self):
        blockers = collections.defaultdict(dict[int, simpy.Resource])

        for way in self._ways:
            for lane in way.lanes:
                blockers[way.id][lane.id] = simpy.Resource(self.env, 1)

        self.blockers = blockers

    def get_conflicting_lane_blockers(
        self, from_way_lane: tuple[Way, Lane], to_way_lane: tuple[Way, Lane]
    ) -> list[simpy.Resource]:
        turn_direction = self._get_way_turn(from_way_lane[0], to_way_lane[0])
        res_blockers: list[simpy.Resource] = []

        res_blockers.append(self.blockers[from_way_lane[0].id][from_way_lane[1].id])
        res_blockers.append(self.blockers[to_way_lane[0].id][to_way_lane[1].id])

        if (
            turn_direction == None and from_way_lane[0].id == to_way_lane[0]
        ):  # Turning back
            pass
        elif turn_direction == Turn.through:
            """
            Block lanes on left side of from_way if turn_direction == Turn.Left or Turn.Through
            Block all lanes on right side
            Block lanes in front of from_way if turn_direction == Turn.Left
            """

            left_way = self.turns[from_way_lane[0].id].left
            if left_way:
                for lane in self._get_in_lanes(left_way):
                    if (
                        len(lane.turns) == 0
                        or Turn.left in lane.turns
                        or Turn.through in lane.turns
                    ):
                        res_blockers.append(self.blockers[left_way.id][lane.id])

            right_way = self.turns[from_way_lane[0].id].right
            if right_way:
                for lane in self._get_in_lanes(right_way):
                    res_blockers.append(self.blockers[right_way.id][lane.id])

            front_way = self.turns[from_way_lane[0].id].through
            if front_way:
                for lane in self._get_in_lanes(front_way):
                    if (
                        len(lane.turns) == 0
                        or Turn.left in lane.turns
                        or Turn.through in lane.turns
                    ):
                        res_blockers.append(self.blockers[front_way.id][lane.id])
        elif turn_direction == Turn.left:
            """
            Block lanes on left side of from_way if turn_direction == Turn.Left or Turn.Through
            Block lanes on right side of from_way if turn_direction == Turn.Left or Turn.Through
            Block lanes in front of from_way if turn_direction == Turn.Through
            """
            left_way = self.turns[from_way_lane[0].id].left
            if left_way:
                for lane in self._get_in_lanes(left_way):
                    if (
                        len(lane.turns) == 0
                        or Turn.left in lane.turns
                        or Turn.through in lane.turns
                    ):
                        res_blockers.append(self.blockers[left_way.id][lane.id])

            right_way = self.turns[from_way_lane[0].id].right
            if right_way:
                for lane in self._get_in_lanes(right_way):
                    if (
                        len(lane.turns) == 0
                        or Turn.left in lane.turns
                        or Turn.through in lane.turns
                    ):
                        res_blockers.append(self.blockers[right_way.id][lane.id])

            front_way = self.turns[from_way_lane[0].id].through
            if front_way:
                for lane in self._get_in_lanes(front_way):
                    if len(lane.turns) == 0 or Turn.through in lane.turns:
                        res_blockers.append(self.blockers[front_way.id][lane.id])
        elif turn_direction == Turn.right:
            """
            Block lanes on left side of from_way if turn_direction == Turn.Through
            Block lanes in front of from_way if turn_direction == Turn.Left
            """
            left_way = self.turns[from_way_lane[0].id].left
            if left_way:
                for lane in self._get_in_lanes(left_way):
                    if len(lane.turns) == 0 or Turn.through in lane.turns:
                        res_blockers.append(self.blockers[left_way.id][lane.id])

            front_way = self.turns[from_way_lane[0].id].through
            if front_way:
                for lane in self._get_in_lanes(front_way):
                    if len(lane.turns) == 0 or Turn.left in lane.turns:
                        res_blockers.append(self.blockers[front_way.id][lane.id])

        return res_blockers

    def _get_in_lanes(self, way: Way) -> list[Lane]:
        return way.lanes.forward if self._is_in_way(way) else way.lanes.backward

    def _update_main_ways(self):
        priorities = [
            way.highway_class.value for way in self._ways
        ]  # highest priority is the lowest value

        max_priority = min(priorities)

        if priorities.count(max_priority) <= 2:
            self.main_ways = [
                way for way in self._ways if way.highway_class.value == max_priority
            ]
        else:
            self.main_ways = []

    # TODO: refactor
    def get_next_way_options(self, way: Way) -> list[NextWayOption]:
        next_way_options: list[NextWayOption] = []

        is_in_way = self._is_in_way(way)

        for next_way in self._ways:
            if next_way == way:
                continue

            turn_direction = self._get_way_turn(way, next_way)

            from_lanes = way.lanes.forward if is_in_way else way.lanes.backward
            can_turn = False

            for from_lane in from_lanes:
                if (
                    len(from_lane.turns) == 0
                    or turn_direction in from_lane.turns
                    or Turn.none in from_lane.turns
                ):
                    can_turn = True
                    break

            if not can_turn:
                continue

            if self._is_in_way(next_way):
                if len(next_way.lanes.backward) > 0:
                    next_way_options.append(NextWayOption(next_way, turn_direction))
            else:
                if len(next_way.lanes.forward) > 0:
                    next_way_options.append(NextWayOption(next_way, turn_direction))

        return next_way_options

    def get_next_lane_options(
        self, from_way: Way, to_way: Way
    ) -> dict[Lane, list[Lane]]:
        turn_direction = self._get_way_turn(from_way, to_way)

        in_lanes = (
            from_way.lanes.forward
            if self._is_in_way(from_way)
            else from_way.lanes.backward
        )
        out_lanes = (
            to_way.lanes.backward if self._is_in_way(to_way) else to_way.lanes.forward
        )

        lane_options: dict[Lane, list[Lane]] = {}

        for lane in in_lanes:
            if len(lane.turns) == 0 or Turn.none in lane.turns:
                lane_options[lane] = out_lanes
            else:
                lanes = [
                    out_lane for out_lane in out_lanes if turn_direction in lane.turns
                ]

                if len(lanes) > 0:
                    lane_options[lane] = lanes

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

    def _get_way_angles(self) -> dict[Way, float]:
        in_ways = [w.id for w in self._ways if w.nodes[-1].id == self.node.id]
        out_ways = [w.id for w in self._ways if w.nodes[0].id == self.node.id]

        way_angle: dict[Way, float] = {}

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
        self.turns = {}

        for way in self._ways:
            this_way_angle = way_angle[way]

            turns = CrossroadTurn(None, None, None)
            turn_count = 0

            for target_way, angle in way_angle.items():
                delta_angle = (angle - this_way_angle) % 360

                if 20 <= delta_angle < 135:
                    if turns.right and way_angle[turns.right] > delta_angle:
                        turns.through = turns.right
                        turns.right = target_way
                    elif turns.right and way_angle[turns.right] < delta_angle:
                        turns.through = target_way
                    else:
                        turns.right = target_way

                    turn_count += 1
                elif 135 <= delta_angle < 225:
                    if turns.through:
                        old_diff = way_angle[turns.through] - 180
                        new_diff = delta_angle - 180

                        if abs(old_diff) < abs(new_diff):
                            if new_diff > 0:
                                turns.left = target_way
                            else:
                                turns.right = target_way
                        else:
                            if old_diff > 0:
                                turns.left = turns.through
                            else:
                                turns.right = turns.through

                            turns.through = target_way
                    else:
                        turns.through = target_way
                    turn_count += 1
                elif 225 <= delta_angle <= 340:
                    if turns.left and way_angle[turns.left] < delta_angle:
                        turns.through = turns.left
                        turns.left = target_way
                    elif turns.left and way_angle[turns.left] > delta_angle:
                        turns.through = target_way
                    else:
                        turns.left = target_way

                    turn_count += 1

            if turn_count == 1 and turns.through == None:
                turns.through = turns.right or turns.left
                turns.right = turns.left = None

            self.turns[way.id] = turns
