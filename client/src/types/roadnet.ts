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

export interface CarEvent {
  time: number;
  car_id: number;
  way?: Way;
  crossroad?: Crossroad;
  lane: Lane;
  position: number;
  speed: number;
}

export interface CrossroadEvent {
  time: number;
  crossroad: Crossroad;
  green_lanes: Lane[];
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
  nodes: LatLng[];
  length: number;
}

export interface Way {
  id: number;
  max_speed: number;
  lanes: Lane[];
}

export interface Crossroad {
  id: number;
  node_id: bigint;
  has_traffic_light: boolean;
  lat: number;
  lng: number;
  lanes: Lane[];
}

export interface Simulation {
  nodes: Node[];
  ways: Way[];
  crossroads: Crossroad[];
  car_events: CarEvent[];
  crossroad_events: CrossroadEvent[];
}
