import {
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
const LANE_STRUCT_SIZE = 4 + 1 + 8;
const CROSSROAD_STRUCT_SIZE = 4 + 8;
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

const parseLane = (view: DataView, offset: number, length: number) => {
  const id = view.getUint32(offset + 0);
  const is_forward = view.getInt8(offset + 4) != 0;

  const turns: Turns[] = [];

  const turns_offset = 5;
  for (let i: Turns = 0; i < TURN_COUNT; i++) {
    const turn = view.getInt8(offset + turns_offset + i * 4);

    if (turn != 0) {
      turns.push(i);
    }
  }

  return {
    id: id,
    is_forward: is_forward,
    turns: turns,
    length: length, // TODO: fix this
  };
};

const getWayLength = (nodes: Node[]) => {
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

const parseWays = (buffer: ArrayBuffer, count: number) => {
  const view = new DataView(buffer);

  const ways: Way[] = [];

  let wayOffset = 0;

  for (let i = 0; i < count; i++) {
    const way_id = view.getUint32(wayOffset);
    const max_speed = view.getUint32(wayOffset + 4);
    const nodes_count = view.getUint32(wayOffset + 8);
    const lanes_count = view.getUint32(wayOffset + 12);

    const nodes: Node[] = [];
    const lanes: Lane[] = [];

    const nodes_offset = wayOffset + 16;
    for (let j = 0; j < nodes_count; j++) {
      nodes.push(parseNode(view, nodes_offset + j * NODE_STRUCT_SIZE));
    }

    const way_length = getWayLength(nodes);

    const lanes_offset = nodes_offset + nodes_count * NODE_STRUCT_SIZE;
    for (let j = 0; j < lanes_count; j++) {
      lanes.push(
        parseLane(view, lanes_offset + j * LANE_STRUCT_SIZE, way_length)
      );
    }

    ways.push({
      id: way_id,
      max_speed: max_speed,
      nodes: nodes,
      lanes: lanes,
    });

    wayOffset = lanes_offset + lanes_count * LANE_STRUCT_SIZE;
  }

  return { ways: ways, size: wayOffset };
};

const parseCrossroads = (buffer: ArrayBuffer, count: number) => {
  const view = new DataView(buffer);

  const crossroads: Crossroad[] = [];

  for (let i = 0; i < count; i++) {
    const crossroad_id = view.getUint32(i * CROSSROAD_STRUCT_SIZE);
    const node_id = view.getBigUint64(i * CROSSROAD_STRUCT_SIZE + 4);

    crossroads.push({
      id: crossroad_id,
      node_id: node_id,
    });
  }

  return { crossroads: crossroads, size: count * CROSSROAD_STRUCT_SIZE };
};

const parseSimulation = (buffer: ArrayBuffer): Simulation => {
  const view = new DataView(buffer);

  const waysCount = view.getInt32(0);
  const crossroadsCount = view.getInt32(4);

  const waysOffset = 8;
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

  return { ways: ways, crossroads: crossroads, events: events };
};

export default parseSimulation;
