import osmium
from utils import LatLng, str_to_int, Turn
from entities import Way, WayLanesProps, Crossroad, Node


class Parser(osmium.SimpleHandler):
    def __init__(self, env):
        osmium.SimpleHandler.__init__(self)
        self.env = env
        self._nodes: dict(int, Node) = {}
        self.ways: list[Way] = []
        self.crossroads: list[Crossroad] = []

    def node(self, n: osmium.osm.Node):
        self._nodes[n.id] = Node(n.id, LatLng(n.location.lat, n.location.lon))

    def way(self, w: osmium.osm.Way):
        maxspeed = str_to_int(w.tags.get("maxspeed", "50"), 50)

        nodes = [self._nodes[node.ref] for node in w.nodes]

        lanes = self._parse_lanes(w)

        new_way = Way(maxspeed, lanes, nodes, w.id)
        self.ways.append(new_way)

    def init_crossroads(self):
        for way in self.ways:
            self._init_way_crossroads(way)

    def _parse_lanes(self, w: osmium.osm.Way) -> WayLanesProps:
        lane_count = str_to_int(w.tags.get("lanes", "0"), 0)
        lane_forward_count = str_to_int(w.tags.get("lanes:forward", "0"), 0)
        lane_backward_count = str_to_int(w.tags.get("lanes:backward", "0"), 0)
        oneway = w.tags.get("oneway") == "yes"

        if lane_count == 0:
            lane_count = 1 if oneway else 2

        if lane_forward_count == 0:
            if lane_backward_count == 0:
                lane_forward_count = lane_count if oneway else lane_count // 2
                lane_backward_count = lane_count - lane_forward_count
            else:
                lane_forward_count = lane_count - lane_backward_count
        else:
            if lane_backward_count == 0:
                lane_backward_count = lane_count - lane_forward_count

        forward_turns = self._parse_turns(w.tags.get("turn:lanes:forward", ""))
        backward_turns = self._parse_turns(w.tags.get("turn:lanes:backward", ""))

        way_lanes = WayLanesProps(
            lane_forward_count, lane_backward_count, forward_turns, backward_turns
        )

        return way_lanes

    def _parse_turns(self, turns_str: str) -> list[list[Turn]]:
        if turns_str == "":
            return None
        turns = turns_str.split("|")
        turns = [turn.split(";") for turn in turns]
        turns = [[Turn[turn] for turn in lane_turns] for lane_turns in turns]

        return turns

    def _init_way_crossroads(self, way: Way):
        prev_crossroad = self._create_or_update_crossroad_on_node(way.nodes[0])
        way.prev_crossroad = prev_crossroad

        next_crossroad = self._create_or_update_crossroad_on_node(way.nodes[-1])
        way.next_crossroad = next_crossroad

    def _create_or_update_crossroad_on_node(self, node: Node) -> Crossroad:
        crossroad = self._get_crossroad(node.id)
        if crossroad is None:
            crossroad = Crossroad(node)
            self.crossroads.append(crossroad)

            way_with_node_in_middle = self._get_way_with_node_in_middle(node)

            if way_with_node_in_middle is not None:
                new_way = way_with_node_in_middle.split(node)
                new_way.next_crossroad = crossroad
                self.ways.append(new_way)

                way_with_node_in_middle.prev_crossroad = crossroad

        return crossroad

    def _get_way_with_node_in_middle(
        self, node: Node
    ) -> Way:  # TODO: what if mulitple ways?
        for way in node.ways:
            if way.nodes[0].id != node.id and way.nodes[-1].id != node.id:
                return way
        return None

    def _get_crossroad(self, node_id: int) -> Crossroad:
        for crossroad in self.crossroads:
            if crossroad.node.id == node_id:
                return crossroad
        return None
