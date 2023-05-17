import simpy

from utils import LatLng, Turn
from entities import Way, Crossroad
from .Lane import Lane


class BlockableLane(Lane):
    def __init__(
        self,
        env: simpy.Environment,
        nodes: list[LatLng],
        way: Way = None,
        crossroad: Crossroad = None,
        is_forward: bool = True,
        turns: list[Turn] = None,
        next_lanes: list[Lane] = None,
    ):
        super().__init__(nodes, way, crossroad, is_forward, turns, next_lanes)
        self.env = env
        self.blocker = simpy.Resource(self.env, capacity=5)
        self.disabled = False

    def disable(self):
        self.disabled = True

    def enable(self):
        self.disabled = False

    def request(self):
        if self.disabled:
            return None
        return self.blocker.request()

    def release(self, request):
        return self.blocker.release(request)

    def is_blocked(self):
        return self.blocker.count > 0

    @property
    def users(self):
        return self.blocker.users
