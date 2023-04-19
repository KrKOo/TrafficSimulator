export interface LatLng {
  lat: number;
  lng: number;
}

export enum Turns {
  none = 0,
  left,
  right,
  through,
  merge_to_right,
  merge_to_left,
  slight_right,
  slight_left,
}

export interface Event {
  time: number;
  car_id: number;
  way: Way;
  lane: Lane;
  position: number;
  speed: number;
}

export interface Node {
  id: bigint;
  lat: number;
  lng: number;
}

export interface Lane {
  id: number;
  is_forward: boolean;
  turns: Turns[];
  length: number;
}

export interface Way {
  id: number;
  max_speed: number;
  nodes: Node[];
  lanes: Lane[];
}

export interface Crossroad {
  id: number;
  node_id: bigint;
  has_traffic_light: boolean;
  lat: number;
  lng: number;
}

export interface Simulation {
  ways: Way[];
  crossroads: Crossroad[];
  events: Event[];
}
