import osmium
from utils import LatLng, str_to_int, Turn
from entities import Way, WayLanesProps, Crossroad, Node
from typing import List


class Parser(osmium.SimpleHandler):
    def __init__(self, env):
        osmium.SimpleHandler.__init__(self)
        self.env = env
        self._nodes = []
        self.ways: List[Way] = []
        self.crossroads: List[Crossroad] = []

    def node(self, n: osmium.osm.Node):
        self._nodes.append([n.id, LatLng(n.location.lat, n.location.lon)])

    def way(self, w: osmium.osm.Way):
        node_dict = dict(self._nodes)

        maxspeed = str_to_int(w.tags.get("maxspeed", "50"), 50)

        nodes = [Node(node.ref, node_dict[node.ref]) for node in w.nodes]

        lanes = self._parse_lanes(w)

        new_way = Way(w.id, maxspeed, lanes, nodes)
        self.ways.append(new_way)

    def init_crossroads(self):
        for way in self.ways:
            self._create_or_update_crossroad(way)

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

    def _parse_turns(self, turns_str: str) -> List[List[Turn]]:
        if turns_str == "":
            return None
        turns = turns_str.split("|")
        turns = [turn.split(";") for turn in turns]
        turns = [[Turn[turn] for turn in lane_turns] for lane_turns in turns]

        return turns

    # TODO: refactor duplication
    def _create_or_update_crossroad(self, way: Way):
        prev_crossroad = self._get_crossroad(way.nodes[0].id)
        if prev_crossroad is None:
            prev_crossroad = Crossroad(way.nodes[0].id, way.nodes[0])
            self.crossroads.append(prev_crossroad)

            way_with_node_in_middle = self._get_way_with_node_in_middle(way.nodes[0])

            if way_with_node_in_middle is not None:
                new_way = way_with_node_in_middle.split(way.nodes[0])
                new_way.next_crossroad = prev_crossroad
                self.ways.append(new_way)

                way_with_node_in_middle.prev_crossroad = prev_crossroad

        way.prev_crossroad = prev_crossroad

        next_crossroad = self._get_crossroad(way.nodes[-1].id)
        if next_crossroad is None:
            next_crossroad = Crossroad(way.nodes[-1].id, way.nodes[-1])
            self.crossroads.append(next_crossroad)

            way_with_node_in_middle = self._get_way_with_node_in_middle(way.nodes[-1])

            if way_with_node_in_middle is not None:
                new_way = way_with_node_in_middle.split(way.nodes[-1])
                new_way.next_crossroad = next_crossroad
                self.ways.append(new_way)

                way_with_node_in_middle.prev_crossroad = next_crossroad

        way.next_crossroad = next_crossroad

    def _get_way_with_node_in_middle(
        self, node: Node
    ) -> Way:  # TODO: what if mulitple ways?
        for way in self.ways:
            for way_node in way.nodes:
                if (
                    way_node.id == node.id
                    and way_node != way.nodes[0]
                    and way_node != way.nodes[-1]
                ):
                    return way
        return None

    def _get_crossroad(self, id: int) -> Crossroad:
        for crossroad in self.crossroads:
            if crossroad.id == id:
                return crossroad
        return None
