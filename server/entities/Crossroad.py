from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from entities import Way

from utils import LatLng


class Crossroad:
    def __init__(self, id: int, pos: LatLng, ways: List[Way]):
        self.id = id
        self.ways = ways
        self.pos = pos
