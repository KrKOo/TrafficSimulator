import math
from utils.types import LatLng


# https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
def haversine(start: LatLng, end: LatLng):
    """Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [start.lng, start.lat, end.lng, end.lat])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371 * c
    return km


def get_point_from_angle_and_distance(
    point: LatLng, angle: float, distance: float
) -> LatLng:
    angle_rad = math.radians(angle)
    lat = point.lat + math.sin(angle_rad) * distance
    lng = point.lng + math.cos(angle_rad) * distance

    return LatLng(lat, lng)
