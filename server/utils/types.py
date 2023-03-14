from enum import Enum


class LatLng:
    def __init__(self, lat: float, lng: float):
        self.lat = lat
        self.lng = lng


Turn = Enum(
    "Turn",
    [
        "none",
        "left",
        "right",
        "through",
        "merge_to_right",
        "merge_to_left",
        "slight_right",
        "slight_left",
    ],
)  # TODO: add other
