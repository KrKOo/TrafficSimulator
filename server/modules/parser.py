import osmium
from utils import LatLng, str_to_int, Turn
from entities import Way, WayLanes
from typing import List

class Parser(osmium.SimpleHandler):
    def __init__(self, env):
        osmium.SimpleHandler.__init__(self)
        self.env = env
        self._nodes = []
        self.ways: List[Way] = []

    def node(self, n: osmium.osm.Node):
        self._nodes.append([n.id, LatLng(n.location.lat, n.location.lon)])

    def way(self, w: osmium.osm.Way):
        node_dict = dict(self._nodes)

        maxspeed = str_to_int(w.tags.get("maxspeed", "50"), 50)
        oneway = w.tags.get("oneway") == "yes"

        nodes = [node_dict[node.ref] for node in w.nodes]

        lanes = self._parse_lanes(w)

        new_way = Way(w.id, maxspeed, lanes, oneway, nodes)

        self.ways.append(new_way)

    def _parse_lanes(self, w: osmium.osm.Way) -> WayLanes:
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

        way_lanes = WayLanes(lane_forward_count, lane_backward_count, forward_turns, backward_turns)

        return way_lanes


    def _parse_turns(self, turns_str: str) -> List[List[Turn]]:
        if(turns_str == ""):
            return []
        turns = turns_str.split("|")
        turns = [turn.split(";") for turn in turns]
        turns = [[Turn[turn] for turn in lane_turns] for lane_turns in turns]

        return turns
