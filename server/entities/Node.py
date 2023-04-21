import struct
from utils import LatLng
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities import Way


class Node:
    def __init__(
        self,
        id: int,
        pos: LatLng,
        has_traffic_light: bool = False,
        ways: list["Way"] = None,
    ):
        self.id = id
        self.pos = pos
        self.has_traffic_light = has_traffic_light
        self._ways: list["Way"] = [] if ways is None else ways

    @property
    def ways(self):
        return self._ways

    def add_way(self, way: "Way"):
        self._ways.append(way)

    def remove_way(self, way: "Way"):
        self._ways.remove(way)

    def pack(self):
        return struct.pack("!Qff", self.id, self.pos.lat, self.pos.lng)
