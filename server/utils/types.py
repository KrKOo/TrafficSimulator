from enum import Enum


class LatLng:
    def __init__(self, lat: float, lng: float):
        self.lat = lat
        self.lng = lng


class Direction(Enum):
    Right = 1
    Left = 2


HighwayClass = Enum(
    "HighwayClass",
    [
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "unclassified",
        "residential",
        "service",
        "motorway_link",
        "trunk_link",
        "primary_link",
        "secondary_link",
        "tertiary_link",
    ],
)

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
)
