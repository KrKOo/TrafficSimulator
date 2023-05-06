import {
  LatLng,
  Simulation,
  Event,
  Way,
  Node,
  Lane,
  Crossroad,
  Turns,
} from 'types/roadnet';
import { haversine } from 'utils/math';

const EVENT_STRUCT_SIZE = 6 * 4;
const NODE_STRUCT_SIZE = 8 + 2 * 4;
const LANE_NODE_STRUCT_SIZE = 8;
const LANE_STRUCT_SIZE = 4 + 4 + 1 + 8;
const CROSSROAD_STRUCT_SIZE = 4 + 8 + 1 + 3 * 4;
const TURN_COUNT = 8;

const parseEvents = (buffer: ArrayBuffer, ways: Way[]) => {
  const view = new DataView(buffer);

  const events: Event[] = [];

  for (let i = 0; i < buffer.byteLength; i += EVENT_STRUCT_SIZE) {
    const time = view.getFloat32(i);
    const car_id = view.getUint32(i + 4);
    const way_id = view.getUint32(i + 8);
    const lane_id = view.getUint32(i + 12);
    const position = view.getFloat32(i + 16);
    const speed = view.getFloat32(i + 20);

    const way = ways.find((way) => way.id == way_id);
    if (!way) {
      continue;
    }

    const lane = way.lanes.find((lane) => lane.id == lane_id);
    if (!lane) {
      continue;
    }

    events.push({
      time: time,
      car_id: car_id,
      way: way,
      lane: lane,
      position: position,
      speed: speed,
    });
  }

  return events;
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

  const nodesOffset = 12;
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

  const eventsOffset = crossroadsOffset + crossroadsSize;
  const events = parseEvents(buffer.slice(eventsOffset), ways);

  return { nodes: nodes, ways: ways, crossroads: crossroads, events: events };
};

export default parseSimulation;
