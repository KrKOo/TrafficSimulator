from enum import Enum
import struct

EventType = Enum('EventType', ['CarUpdate'])

class Event:
    def __init__(self, evn_type, car_id, way_id, lane_id, position, speed):
        self.time: float = None
        self.type: EventType = evn_type
        self.car_id: int = car_id
        self.position: float = position
        self.way_id: int = way_id
        self.lane_id: int = lane_id
        self.speed: float = speed

    def pack(self):
        data = struct.pack("!fIIIff", self.time, self.car_id, self.way_id, self.lane_id, self.position, self.speed)

        return data

    def get_data(self):
        return {
            "time": self.time,
            "type": self.type.name,
            "car_id": self.car_id,
            "way_id": self.way_id,
            "lane_id": self.lane_id,
            "position": self.position,
            "speed": self.speed,
        }
