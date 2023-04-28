import math
from entities import Node, Way
from utils import LatLng


def is_incoming_way(node: Node, way: Way) -> bool:
    if way.nodes[-1].id == node.id:
        return True
    elif way.nodes[0].id == node.id:
        return False

    assert True, f"Way {way.id} is not connected to node {node.id}"


def angle_between_nodes(node1: Node, node2: Node) -> float:
    delta_lng = node2.pos.lng - node1.pos.lng
    delta_lat = node2.pos.lat - node1.pos.lat

    angle = math.atan2(delta_lat, delta_lng)
    angle = (angle * 180 / math.pi) % 360

    return angle
