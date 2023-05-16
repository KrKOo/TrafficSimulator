import struct


class CarEvent:
    def __init__(
        self,
        car_id: int,
        way_id: int | None,
        crossroad_id: int | None,
        lane_id: int,
        position: float,
        speed: float,
    ):
        self.time: float = None
        self.car_id = car_id
        self.position = position
        self.way_id = way_id if way_id is not None else -1
        self.crossroad_id = crossroad_id if crossroad_id is not None else -1
        self.lane_id = lane_id
        self.speed = speed

    def pack(self):
        data = struct.pack(
            "!fIiiIff",
            self.time,
            self.car_id,
            self.way_id,
            self.crossroad_id,
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
            "crossroad_id": self.crossroad_id,
            "lane_id": self.lane_id,
            "position": self.position,
            "speed": self.speed,
        }
