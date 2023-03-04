from typing import List
from .Way import Way

class Crossroad:
    def __init__(self, id: int, ways: List[Way]):
        self.id = id
        self.ways = ways
