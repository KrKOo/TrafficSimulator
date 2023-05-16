from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.Crossroad import BlockableLane

import struct


class CrossroadEvent:
    def __init__(
        self,
        crossroad_id: int,
        green_lanes: list[BlockableLane],
    ):
        self.time: float = None
        self.crossroad_id = crossroad_id if crossroad_id is not None else -1
        self.green_lanes = green_lanes

    def pack(self):
        lane_ids = [lane.id for lane in self.green_lanes]

        lanes_bytes = struct.pack("!" + "I" * len(self.green_lanes), *lane_ids)

        event_bytes = struct.pack(
            "!fII",
            self.time,
            self.crossroad_id,
            len(self.green_lanes),
        )

        return event_bytes + lanes_bytes

    def get_data(self):
        return {
            "time": self.time,
            "crossroad_id": self.crossroad_id,
            "green_lanes": [lane.id for lane in self.green_lanes],
        }
