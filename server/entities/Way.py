from utils import Turn, HighwayClass
import struct
from .Node import Node
from .Road import Road
from .Lane import Lane
from .Crossroad import Crossroad
from .Entity import EntityBase, WithId


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
        # TODO: railway, psv, vehicle lanes


class WayLanes:
    def __init__(self, forward: list[Lane], backward: list[Lane]):
        self.forward = forward
        self.backward = backward

        for lane in self.forward:
            lane.is_forward = True

        for lane in self.backward:
            lane.is_forward = False

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
        self.lanes = self._init_lanes(lanes_props)
        self._nodes = []
        self.nodes = nodes if nodes is not None else []

        self.roads = self._init_roads()

        self._next_crossroad: Crossroad = None
        self._prev_crossroad: Crossroad = None

    @property
    def length(self):
        return sum([road.length for road in self.roads])

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, nodes: list[Node]):
        for node in self._nodes:
            if self in node.ways:
                node.remove_way(self)

        self._nodes = nodes

        for node in self._nodes:
            if self not in node.ways:
                node.add_way(self)

    def pack(self):
        lanes_list = []
        lane_struct = struct.Struct("!I?????????")

        for lane in self.lanes.forward + self.lanes.backward:
            lanes_list.append(
                lane_struct.pack(
                    lane.id,
                    lane.is_forward,
                    Turn.none in lane.turns,
                    Turn.left in lane.turns,
                    Turn.right in lane.turns,
                    Turn.through in lane.turns,
                    Turn.merge_to_right in lane.turns,
                    Turn.merge_to_left in lane.turns,
                    Turn.slight_right in lane.turns,
                    Turn.slight_left in lane.turns,
                )
            )
        lanes_bytes = b"".join(lanes_list)

        nodes_list = []

        for node in self.nodes:
            nodes_list.append(struct.pack("!Q", node.id))

        nodes_bytes = b"".join(nodes_list)

        way_struct = struct.Struct(f"!IIII")

        return (
            way_struct.pack(self.id, self.max_speed, len(nodes_list), len(lanes_list))
            + nodes_bytes
            + lanes_bytes
        )

    def _init_lanes(self, lanes_props: WayLanesProps) -> WayLanes:
        if lanes_props.forward_lane_turn is None:
            forward_lanes = [Lane(True) for _ in range(lanes_props.forward_lane_count)]
        else:
            forward_lanes = [
                Lane(True, turns=lane_turn)
                for lane_turn in lanes_props.forward_lane_turn
            ]

        if lanes_props.backward_lane_turn is None:
            backward_lanes = [
                Lane(False) for _ in range(lanes_props.backward_lane_count)
            ]
        else:
            backward_lanes = [
                Lane(False, turns=lane_turn)
                for lane_turn in lanes_props.backward_lane_turn
            ]

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
