from enum import Enum
import struct


class Event:
    def __init__(self, car_id, way_id, lane_id, position, speed):
        self.time: float = None
        self.car_id: int = car_id
        self.position: float = position
        self.way_id: int = way_id
        self.lane_id: int = lane_id
        self.speed: float = speed

    def pack(self):
        data = struct.pack(
            "!fIIIff",
            self.time,
            self.car_id,
            self.way_id,
            self.lane_id,
            self.position,
            self.speed,
        )

        return data

    def get_data(self):
        return {
            "time": self.time,
            "car_id": self.car_id,
            "way_id": self.way_id,
            "lane_id": self.lane_id,
            "position": self.position,
            "speed": self.speed,
        }
