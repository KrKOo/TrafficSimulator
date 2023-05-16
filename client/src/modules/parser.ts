import {
  LatLng,
  Simulation,
  CarEvent,
  CrossroadEvent,
  Way,
  Node,
  Lane,
  Crossroad,
  Turns,
} from 'types/roadnet';
import { haversine } from 'utils/math';

const CAR_EVENT_STRUCT_SIZE = 7 * 4;
const CROSSROAD_EVENT_STRUCT_SIZE = 3 * 4;
const NODE_STRUCT_SIZE = 8 + 2 * 4;
const LANE_NODE_STRUCT_SIZE = 8;
const LANE_STRUCT_SIZE = 4 + 4 + 1 + 8;
const TURN_COUNT = 8;

const parseCarEvents = (
  buffer: ArrayBuffer,
  count: number,
  ways: Way[],
  crossroads: Crossroad[]
) => {
  const view = new DataView(buffer);

  const events: CarEvent[] = [];

  let eventOffset = 0;

  for (let i = 0; i < count; i++) {
    const time = view.getFloat32(eventOffset);
    const car_id = view.getUint32(eventOffset + 4);
    const way_id = view.getInt32(eventOffset + 8);
    const crossroad_id = view.getInt32(eventOffset + 12);
    const lane_id = view.getUint32(eventOffset + 16);
    const position = view.getFloat32(eventOffset + 20);
    const speed = view.getFloat32(eventOffset + 24);

    let way: Way | undefined = undefined;
    if (way_id != -1) {
      way = ways.find((way) => way.id == way_id);
      if (!way) {
        continue;
      }
    }

    let crossroad: Crossroad | undefined = undefined;
    if (crossroad_id != -1) {
      crossroad = crossroads.find((crossroad) => crossroad.id == crossroad_id);
      if (!crossroad) {
        continue;
      }
    }

    const lane_parent = way || crossroad;
    const lane = lane_parent!.lanes.find((lane) => lane.id == lane_id);
    if (!lane) {
      continue;
    }

    events.push({
      time: time,
      car_id: car_id,
      way: way,
      crossroad: crossroad,
      lane: lane,
      position: position,
      speed: speed,
    });

    eventOffset += CAR_EVENT_STRUCT_SIZE;
  }

  return { events: events, size: eventOffset };
};

const parseCrossroadEvents = (
  buffer: ArrayBuffer,
  count: number,
  crossroads: Crossroad[]
) => {
  const view = new DataView(buffer);

  const events: CrossroadEvent[] = [];

  let eventOffset = 0;

  for (let i = 0; i < count; i++) {
    const time = view.getFloat32(eventOffset);
    const crossroad_id = view.getUint32(eventOffset + 4);
    const green_lane_count = view.getUint32(eventOffset + 8);

    let crossroad: Crossroad | undefined = undefined;
    crossroad = crossroads.find((crossroad) => crossroad.id == crossroad_id);
    if (!crossroad) {
      continue;
    }

    const green_lanes: Lane[] = [];
    for (let i = 0; i < green_lane_count; i++) {
      const lane_id = view.getInt32(eventOffset + 12 + i * 4);
      const lane = crossroad.lanes.find((lane) => lane.id == lane_id);
      if (!lane) {
        continue;
      }

      green_lanes.push(lane);
    }

    events.push({
      time: time,
      crossroad: crossroad,
      green_lanes: green_lanes,
    });

    eventOffset += CROSSROAD_EVENT_STRUCT_SIZE + green_lane_count * 4;
  }

  return { events: events, size: eventOffset };
};

const parseNode = (view: DataView, offset: number) => {
  const id = view.getBigUint64(offset + 0);
  const lat = view.getFloat32(offset + 8);
  const lng = view.getFloat32(offset + 12);

  return {
    id: id,
    lat: lat,
    lng: lng,
  };
};

const parseLane = (view: DataView, offset: number) => {
  const id = view.getUint32(offset + 0);
  const node_count = view.getUint32(offset + 4);
  const is_forward = view.getInt8(offset + 8) != 0;

  const turns: Turns[] = [];

  const turns_offset = offset + 9;
  for (let i: Turns = 0; i < TURN_COUNT; i++) {
    const turn = view.getInt8(turns_offset + i * 1);

    if (turn != 0) {
      turns.push(i);
    }
  }

  let nodes: LatLng[] = [];
  const nodes_offset = turns_offset + TURN_COUNT;

  for (let i = 0; i < node_count; i++) {
    const lat = view.getFloat32(nodes_offset + i * 8);
    const lng = view.getFloat32(nodes_offset + i * 8 + 4);

    nodes.push({ lat: lat, lng: lng });
  }

  return {
    lane: {
      id: id,
      is_forward: is_forward,
      turns: turns,
      nodes: nodes,
      length: getLaneLength(nodes),
    },
    size: LANE_STRUCT_SIZE + node_count * LANE_NODE_STRUCT_SIZE,
  };
};

const getLaneLength = (nodes: LatLng[]) => {
  let length = 0;

  for (let i = 0; i < nodes.length - 1; i++) {
    const node1 = nodes[i];
    const node2 = nodes[i + 1];

    length += haversine(
      { lat: node1.lat, lng: node1.lng },
      { lat: node2.lat, lng: node2.lng }
    );
  }

  return length;
};

const parseNodes = (buffer: ArrayBuffer, count: number) => {
  const view = new DataView(buffer);

  const nodes: Node[] = [];

  for (let i = 0; i < count; i++) {
    nodes.push(parseNode(view, i * NODE_STRUCT_SIZE));
  }

  return { nodes: nodes, size: count * NODE_STRUCT_SIZE };
};

const parseWays = (buffer: ArrayBuffer, count: number) => {
  const view = new DataView(buffer);

  const ways: Way[] = [];

  let wayOffset = 0;

  for (let i = 0; i < count; i++) {
    const way_id = view.getUint32(wayOffset);
    const max_speed = view.getUint32(wayOffset + 4);
    const lane_count = view.getUint32(wayOffset + 8);

    const lanes: Lane[] = [];

    let lanes_offset = wayOffset + 12;
    for (let j = 0; j < lane_count; j++) {
      const { lane, size } = parseLane(view, lanes_offset);
      lanes_offset += size;
      lanes.push(lane);
    }

    ways.push({
      id: way_id,
      max_speed: max_speed,
      lanes: lanes,
    });

    wayOffset = lanes_offset;
  }

  return { ways: ways, size: wayOffset };
};

const parseCrossroads = (buffer: ArrayBuffer, count: number) => {
  const view = new DataView(buffer);

  const crossroads: Crossroad[] = [];
  let crossroad_offset = 0;

  for (let i = 0; i < count; i++) {
    const crossroad_id = view.getUint32(crossroad_offset);
    const node_id = view.getBigUint64(crossroad_offset + 4);
    const has_traffic_light = view.getInt8(crossroad_offset + 12) != 0;
    const lat = view.getFloat32(crossroad_offset + 13);
    const lng = view.getFloat32(crossroad_offset + 17);
    const lane_count = view.getUint32(crossroad_offset + 21);

    const lanes: Lane[] = [];
    let lanes_offset = crossroad_offset + 25;

    for (let j = 0; j < lane_count; j++) {
      const { lane, size } = parseLane(view, lanes_offset);
      lanes_offset += size;
      lanes.push(lane);
    }

    crossroads.push({
      id: crossroad_id,
      node_id: node_id,
      has_traffic_light: has_traffic_light,
      lat: lat,
      lng: lng,
      lanes: lanes,
    });

    crossroad_offset = lanes_offset;
  }

  return { crossroads: crossroads, size: crossroad_offset };
};

const parseSimulation = (buffer: ArrayBuffer): Simulation => {
  const view = new DataView(buffer);

  const nodesCount = view.getInt32(0);
  const waysCount = view.getInt32(4);
  const crossroadsCount = view.getInt32(8);
  const carEventCount = view.getInt32(12);
  const crossroadEventCount = view.getInt32(16);

  console.log(
    nodesCount,
    waysCount,
    crossroadsCount,
    carEventCount,
    crossroadEventCount
  );

  const nodesOffset = 20;
  const { nodes, size: nodesSize } = parseNodes(
    buffer.slice(nodesOffset),
    nodesCount
  );

  const waysOffset = nodesOffset + nodesSize;
  const { ways, size: waysSize } = parseWays(
    buffer.slice(waysOffset),
    waysCount
  );

  const crossroadsOffset = waysOffset + waysSize;
  const { crossroads, size: crossroadsSize } = parseCrossroads(
    buffer.slice(crossroadsOffset),
    crossroadsCount
  );

  const carEventsOffset = crossroadsOffset + crossroadsSize;
  const { events: carEvents, size: carEventsSize } = parseCarEvents(
    buffer.slice(carEventsOffset),
    carEventCount,
    ways,
    crossroads
  );

  const crossroadEventsOffset = carEventsOffset + carEventsSize;
  const { events: crossroadEvents, size: crossroadEventsSize } =
    parseCrossroadEvents(
      buffer.slice(crossroadEventsOffset),
      crossroadEventCount,
      crossroads
    );

  return {
    nodes: nodes,
    ways: ways,
    crossroads: crossroads,
    car_events: carEvents,
    crossroad_events: crossroadEvents,
  };
};

export default parseSimulation;
