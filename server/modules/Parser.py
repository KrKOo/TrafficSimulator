import osmium
import simpy
from utils import LatLng, str_to_int, Turn, HighwayClass
from entities import Way, WayLanesProps, Crossroad, Node, Calendar


class Parser(osmium.SimpleHandler):
    def __init__(self, env: simpy.Environment, calendar: Calendar):
        osmium.SimpleHandler.__init__(self)
        self.env = env
        self.calendar = calendar
        self._nodes: dict(int, Node) = {}
        self.ways: list[Way] = []
        self.crossroads: list[Crossroad] = []

    def parse(self, filename):
        self.apply_file(filename)
        self.init_crossroads()
        self.remove_short_way_segments()

    def node(self, n: osmium.osm.Node):
        has_traffic_light = n.tags.get("highway") == "traffic_signals"
        self._nodes[n.id] = Node(
            n.id, LatLng(n.location.lat, n.location.lon), has_traffic_light
        )

    def way(self, w: osmium.osm.Way):
        maxspeed = str_to_int(w.tags.get("maxspeed", "50"), 50)
        highway_class = HighwayClass[w.tags.get("highway", "unclassified")]

        nodes = [self._nodes[node.ref] for node in w.nodes]

        lanes = self._parse_lanes(w)

        new_way = Way(maxspeed, highway_class, lanes, nodes, w.id)
        self.ways.append(new_way)

    def init_crossroads(self):
        for way in self.ways:
            self._init_way_crossroads(way)

    def remove_short_way_segments(self):
        for way in self.ways:
            way.remove_short_segments()

    def pack(self):
        nodes_list = [node.pack() for node in self._nodes.values()]
        ways_list = [way.pack() for way in self.ways]
        crossroads_list = [crossroad.pack() for crossroad in self.crossroads]

        return (
            b"".join(nodes_list) + b"".join(ways_list) + b"".join(crossroads_list),
            (len(nodes_list), len(ways_list), len(crossroads_list)),
        )

    def _parse_lanes(self, w: osmium.osm.Way) -> WayLanesProps:
        lane_count = str_to_int(w.tags.get("lanes", "0"), 0)
        lane_forward_count = str_to_int(w.tags.get("lanes:forward", "0"), 0)
        lane_backward_count = str_to_int(w.tags.get("lanes:backward", "0"), 0)

        # Filtering out non-car lanes
        psv_lanes_forward = w.tags.get("psv:lanes:forward", "")
        psv_lane_forward_count = psv_lanes_forward.split("|").count("yes")

        railway_lanes_forward = w.tags.get("railway:lanes:forward", "")
        railway_lane_forward_count = railway_lanes_forward.split("|").count("tram")

        psv_lanes_backward = w.tags.get("psv:lanes:backward", "")
        psv_lane_backward_count = psv_lanes_backward.split("|").count("yes")

        railway_lanes_backward = w.tags.get("railway:lanes:backward", "")
        railway_lane_backward_count = railway_lanes_backward.split("|").count("tram")

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

        non_car_lane_forward_count = max(
            psv_lane_forward_count, railway_lane_forward_count
        )
        non_car_lane_backward_count = max(
            psv_lane_backward_count, railway_lane_backward_count
        )
        if lane_forward_count > non_car_lane_forward_count:
            lane_forward_count -= non_car_lane_forward_count
        if lane_backward_count > non_car_lane_backward_count:
            lane_backward_count -= non_car_lane_backward_count

        forward_turns = self._parse_turns(w.tags.get("turn:lanes:forward", ""))
        backward_turns = self._parse_turns(w.tags.get("turn:lanes:backward", ""))

        # Reverse the arrays since the simulation uses the opposite order than OSM
        forward_turns = (
            forward_turns[-lane_forward_count:][::-1] if forward_turns else None
        )
        backward_turns = (
            backward_turns[-lane_backward_count:][::-1] if backward_turns else None
        )

        way_lanes = WayLanesProps(
            lane_forward_count, lane_backward_count, forward_turns, backward_turns
        )

        return way_lanes

    def _parse_turns(self, turns_str: str) -> list[list[Turn]]:
        if turns_str == "":
            return None
        turns = turns_str.split("|")
        turns = [turn.split(";") for turn in turns]

        res = []

        for lane_turns in turns:
            lane_res = []
            for turn in lane_turns:
                if not turn:
                    continue

                enum_turn = Turn[turn]

                if enum_turn == Turn.slight_left or enum_turn == Turn.merge_to_left:
                    lane_res.append(Turn.left)
                    lane_res.append(Turn.through)

                elif enum_turn == Turn.slight_right or enum_turn == Turn.merge_to_right:
                    lane_res.append(Turn.right)
                    lane_res.append(Turn.through)
                else:
                    lane_res.append(enum_turn)
            res.append(lane_res)

        return res

    def _init_way_crossroads(self, way: Way):
        prev_crossroad = self._create_or_update_crossroad_on_node(way.nodes[0])
        way.prev_crossroad = prev_crossroad

        next_crossroad = self._create_or_update_crossroad_on_node(way.nodes[-1])
        way.next_crossroad = next_crossroad

    def _create_or_update_crossroad_on_node(self, node: Node) -> Crossroad:
        crossroad = self._get_crossroad(node.id)
        if crossroad is None:
            crossroad = Crossroad(self.env, self.calendar, node)
            self.crossroads.append(crossroad)

            way_with_node_in_middle = self._get_way_with_node_in_middle(node)

            if way_with_node_in_middle is not None:
                new_way = way_with_node_in_middle.split(node)
                new_way.next_crossroad = crossroad
                self.ways.append(new_way)

                way_with_node_in_middle.prev_crossroad = crossroad

        return crossroad

    def _get_way_with_node_in_middle(self, node: Node) -> Way:
        for way in node.ways:
            if way.nodes[0].id != node.id and way.nodes[-1].id != node.id:
                return way
        return None

    def _get_crossroad(self, node_id: int) -> Crossroad:
        for crossroad in self.crossroads:
            if crossroad.node.id == node_id:
                return crossroad
        return None
