from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from entities import Way

from utils import LatLng
from typing import Tuple
from .Node import Node
from .Lane import Lane


class NextOption:
    def __init__(self, way: Way, lanes: List[Lane]):
        self.way = way
        self.lanes = lanes


class Crossroad:
    def __init__(self, id: int, node: Node, ways: List[Way] = None):
        self.id = id
        self.ways = ways if ways is not None else []
        self.node = node

    # TODO: add lane parameter or something... idk
    def get_next_options(self, way: Way) -> List[NextOption]:
        next_options: List[NextOption] = []

        in_ways = [w for w in self.ways if w.nodes[-1].id == self.node.id]
        out_ways = [w for w in self.ways if w.nodes[0].id == self.node.id]

        for next_way in self.ways:
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
