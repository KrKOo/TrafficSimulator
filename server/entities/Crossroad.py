from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.Way import Way

import simpy
import collections
import struct
import math
import random

from .Node import Node
from .Lane import Lane
from .BlockableLane import BlockableLane
from .Calendar import Calendar
from .CrossroadEvent import CrossroadEvent
from .Entity import EntityBase, WithId
from utils import Turn
from utils.map_geometry import is_incoming_way, angle_between_nodes
from utils.globals import TRAFFIC_LIGHT_DISABLED_TIME, TRAFFIC_LIGHT_INTERVAL


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
    def __init__(self, env: simpy.Environment, calendar: Calendar, node: Node):
        super().__init__()
        self.id = next(self._ids)
        self.env = env
        self.calendar = calendar
        self._ways: list[Way] = []
        self.node: Node = node
        self.turns: dict[Way, CrossroadTurn] = {}
        self.blockers: collections.defaultdict[int, dict[int, simpy.Resource]] = {}
        self.lanes: list[BlockableLane] = []
        self.main_ways: list[Way] = []

        self._semaphore_process = (
            self.env.process(self.semaphore_process())
            if self.has_traffic_light
            else None
        )

    def pack(self):
        lanes_bytes = b"".join([lane.pack() for lane in self.lanes])

        crossroad_struct = struct.Struct("!IQ?ffI")
        return (
            crossroad_struct.pack(
                self.id,
                self.node.id,
                self.has_traffic_light,
                self.node.pos.lat,
                self.node.pos.lng,
                len(self.lanes),
            )
            + lanes_bytes
        )

    @property
    def has_traffic_light(self):
        return self.node.has_traffic_light

    @property
    def ways(self) -> list[Way]:
        return self._ways

    def add_way(self, way: Way):
        self._ways.append(way)
        self.update()

    def remove_way(self, way: Way):
        self._ways.remove(way)
        self.update()

    def update(self):
        self._update_turns()
        self._update_main_ways()
        self._update_lanes()

    def _update_lanes(self):
        self.lanes = []

        for from_way in self._ways:
            is_from_way_incoming = is_incoming_way(self.node, from_way)
            for to_way in self._ways:
                if from_way == to_way:
                    continue
                is_to_way_incoming = is_incoming_way(self.node, to_way)
                lane_options = self.get_next_lane_options(from_way, to_way)

                for from_lane, to_lanes in lane_options.items():
                    for to_lane in to_lanes:
                        from_node = (
                            from_lane.nodes[-1]
                            if is_from_way_incoming
                            else from_lane.nodes[0]
                        )
                        to_node = (
                            to_lane.nodes[-1]
                            if is_to_way_incoming
                            else to_lane.nodes[0]
                        )
                        new_crossroad_lane = BlockableLane(
                            self.env,
                            [from_node, to_node],
                            crossroad=self,
                            next_lanes=[to_lane],
                        )
                        self.lanes.append(new_crossroad_lane)
                        from_lane.next_lanes.append(new_crossroad_lane)

    def get_lane(self, from_lane: Lane, to_lane: Lane) -> BlockableLane:
        for lane in self.lanes:
            if lane.nodes[0] == (
                from_lane.nodes[0]
                if not is_incoming_way(self.node, from_lane.way)
                else from_lane.nodes[-1]
            ) and lane.nodes[-1] == (
                to_lane.nodes[-1]
                if is_incoming_way(self.node, to_lane.way)
                else to_lane.nodes[0]
            ):
                return lane
        return None

    def disable_lanes_beginning_on_way(self, way: Way):
        if way is None:
            return

        for lane in self.lanes:
            if self.lane_begin_way(lane) == way:
                lane.disable()

    def enable_all_lanes(self):
        for lane in self.lanes:
            lane.enable()

    def disable_all_lanes(self):
        for lane in self.lanes:
            lane.disable()

    @property
    def enabled_lanes(self):
        return [lane for lane in self.lanes if not lane.disabled]

    def calendar_crossroad_update(self):
        self.calendar.add_crossroad_event(CrossroadEvent(self.id, self.enabled_lanes))

    def semaphore_process(self):
        dir1 = (self.ways[0], self.turns[self.ways[0]].through)
        dir2 = (self.turns[self.ways[0]].left, self.turns[self.ways[0]].right)

        # dir1 is always green at the beginning
        self.enable_all_lanes()
        self.disable_lanes_beginning_on_way(dir2[0])
        self.disable_lanes_beginning_on_way(dir2[1])
        self.calendar_crossroad_update()

        # switch to the next state after a random time
        yield self.env.timeout(random.randint(0, TRAFFIC_LIGHT_INTERVAL))

        while True:
            self.disable_all_lanes()
            self.calendar_crossroad_update()
            yield self.env.timeout(TRAFFIC_LIGHT_DISABLED_TIME)

            self.enable_all_lanes()
            self.disable_lanes_beginning_on_way(dir1[0])
            self.disable_lanes_beginning_on_way(dir1[1])
            self.calendar_crossroad_update()

            yield self.env.timeout(TRAFFIC_LIGHT_INTERVAL)
            self.disable_all_lanes()
            self.calendar_crossroad_update()

            yield self.env.timeout(TRAFFIC_LIGHT_DISABLED_TIME)
            self.enable_all_lanes()
            self.disable_lanes_beginning_on_way(dir2[0])
            self.disable_lanes_beginning_on_way(dir2[1])
            self.calendar_crossroad_update()

            yield self.env.timeout(TRAFFIC_LIGHT_INTERVAL)

    def lane_begin_way(self, lane: Lane) -> Way:
        for way in self._ways:
            way_in_lanes = (
                way.lanes.forward
                if is_incoming_way(self.node, way)
                else way.lanes.backward
            )

            for way_lane in way_in_lanes:
                if lane in way_lane.next_lanes:
                    return way

    def lane_end_way(self, lane: Lane) -> Way:
        next_lane_count = len(lane.next_lanes)

        if next_lane_count == 0:
            return None
        elif next_lane_count == 1:
            return lane.next_lanes[0].way
        else:
            return lane.way

    def lanes_to_right(self, lane: Lane) -> list[Lane]:
        lanes = []
        next_lane = lane.right

        while next_lane is not None:
            lanes.append(next_lane)
            next_lane = next_lane.right

        return lanes

    def lanes_to_left(self, lane: Lane) -> list[Lane]:
        lanes = []
        next_lane = lane.left

        while next_lane is not None:
            lanes.append(next_lane)
            next_lane = next_lane.left

        return lanes

    def get_conflicting_lanes(
        self, from_way_lane: tuple[Way, Lane], to_way_lane: tuple[Way, Lane]
    ) -> list[BlockableLane]:
        from_way, from_lane = from_way_lane
        to_way, to_lane = to_way_lane
        crossing_lane = self.get_lane(from_lane, to_lane)

        turn_direction = self._get_way_turn(from_way_lane[0], to_way_lane[0])
        res_lanes: list[BlockableLane] = []

        if (
            turn_direction == None and from_way_lane[0].id == to_way_lane[0].id
        ):  # Turning back
            pass
        elif turn_direction == Turn.through:
            """
            ANY - from_lane -> to_lane
            right -> not to_lane.right
            left -> right_way | to_lane.right
            through -> right_way
            """

            for lane in self.lanes:
                lane_begin_way = self.lane_begin_way(lane)
                lane_end_way = self.lane_end_way(lane)

                if (
                    (to_lane in lane.next_lanes and lane != crossing_lane)
                    or (
                        lane_begin_way == self.turns[from_way].right
                        and (lane.next_lanes[0] not in self.lanes_to_right(to_lane))
                    )
                    or (
                        lane_begin_way == self.turns[from_way].left
                        and (
                            lane_end_way == self.turns[from_way].right
                            or lane.next_lanes[0] in self.lanes_to_left(to_lane)
                        )
                    )
                    or (
                        lane_begin_way == self.turns[from_way].through
                        and lane_end_way == self.turns[from_way].right
                    )
                ):
                    res_lanes.append(lane)

        elif turn_direction == Turn.left:
            """
            ANY - from_lane -> to_lane
            right -> to_lane.left | from_way
            left -> through_way | right_way
            through -> from_way | to_lane.left
            """

            for lane in self.lanes:
                lane_begin_way = self.lane_begin_way(lane)
                lane_end_way = self.lane_end_way(lane)

                if (
                    (to_lane in lane.next_lanes and lane != crossing_lane)
                    or (
                        lane_begin_way == self.turns[from_way].right
                        and (
                            lane.next_lanes[0] in self.lanes_to_left(to_lane)
                            or lane_end_way == from_way
                        )
                    )
                    or (
                        lane_begin_way == self.turns[from_way].left
                        and (
                            lane_end_way == self.turns[from_way].through
                            or lane_end_way == self.turns[from_way].right
                        )
                    )
                    or (
                        lane_begin_way == self.turns[from_way].through
                        and (
                            lane_end_way == from_way
                            or lane.next_lanes[0] in self.lanes_to_left(to_lane)
                        )
                    )
                ):
                    res_lanes.append(lane)

        elif turn_direction == Turn.right:
            """
            ANY - from_lane -> to_lane | to_lane.right
            """

            for lane in self.lanes:
                lane_begin_way = self.lane_begin_way(lane)
                lane_end_way = self.lane_end_way(lane)

                if (
                    to_lane in lane.next_lanes and lane != crossing_lane
                ) or lane.next_lanes[0] in self.lanes_to_right(to_lane):
                    res_lanes.append(lane)

        for lane in res_lanes:
            if lane in from_lane.next_lanes:
                res_lanes.remove(lane)

        return res_lanes

    def _get_in_lanes(self, way: Way) -> list[Lane]:
        return (
            way.lanes.forward if is_incoming_way(self.node, way) else way.lanes.backward
        )

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

    def get_next_way_options(self, way: Way) -> list[NextWayOption]:
        next_way_options: list[NextWayOption] = []

        is_in_way = is_incoming_way(self.node, way)

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

            if is_incoming_way(self.node, next_way):
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
            if is_incoming_way(self.node, from_way)
            else from_way.lanes.backward
        )
        out_lanes = (
            to_way.lanes.backward
            if is_incoming_way(self.node, to_way)
            else to_way.lanes.forward
        )

        lane_options: dict[Lane, list[Lane]] = {}

        for idx, lane in enumerate(in_lanes):
            if len(lane.turns) == 0 or Turn.none in lane.turns:
                if len(out_lanes) == len(in_lanes):
                    lane_options[lane] = [out_lanes[idx]]
                else:
                    lane_options[lane] = out_lanes
            else:
                lanes = [
                    out_lane for out_lane in out_lanes if turn_direction in lane.turns
                ]

                if len(lanes) == 0:
                    continue

                if len(lanes) == len(in_lanes):
                    lane_options[lane] = [lanes[idx]]
                else:
                    lane_options[lane] = lanes

        return lane_options

    def _get_way_turn(self, from_way: Way, to_way: Way):
        way_turns = self.turns[from_way]

        if way_turns.through == to_way:
            return Turn.through
        elif way_turns.left == to_way:
            return Turn.left
        elif way_turns.right == to_way:
            return Turn.right

        return None

    def _get_way_angles(self) -> dict[Way, float]:
        way_angle: dict[Way, float] = {}

        for way in self._ways:
            is_in_way = is_incoming_way(self.node, way)

            if is_in_way:
                angle = angle_between_nodes(self.node, way.nodes[-2])
            else:
                angle = angle_between_nodes(self.node, way.nodes[1])

            way_angle[way] = angle

        return way_angle

    def _update_turns(self):
        """Calculate the ralative directions of the ways."""
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

            self.turns[way] = turns
