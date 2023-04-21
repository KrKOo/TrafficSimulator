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
const CROSSROAD_STRUCT_SIZE = 4 + 8 + 1 + 2 * 4;
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

const parseNodes = (buffer: ArrayBuffer, count: number) => {
  const view = new DataView(buffer);

  const nodes: Node[] = [];

  for (let i = 0; i < count; i++) {
    nodes.push(parseNode(view, i * NODE_STRUCT_SIZE));
  }

  return { nodes: nodes, size: count * NODE_STRUCT_SIZE };
};

const parseWays = (buffer: ArrayBuffer, count: number, nodes: Node[]) => {
  const view = new DataView(buffer);

  const ways: Way[] = [];

  let wayOffset = 0;

  for (let i = 0; i < count; i++) {
    const way_id = view.getUint32(wayOffset);
    const max_speed = view.getUint32(wayOffset + 4);
    const nodes_count = view.getUint32(wayOffset + 8);
    const lanes_count = view.getUint32(wayOffset + 12);

    const _nodes: Node[] = [];
    const lanes: Lane[] = [];

    const nodes_offset = wayOffset + 16;
    for (let j = 0; j < nodes_count; j++) {
      const nodeId = view.getBigUint64(nodes_offset + j * 8);
      const node = nodes.find((node) => node.id == nodeId);
      if (node) {
        _nodes.push(node);
      }
    }

    const way_length = getWayLength(_nodes);

    const lanes_offset = nodes_offset + nodes_count * 8;
    for (let j = 0; j < lanes_count; j++) {
      lanes.push(
        parseLane(view, lanes_offset + j * LANE_STRUCT_SIZE, way_length)
      );
    }

    ways.push({
      id: way_id,
      max_speed: max_speed,
      nodes: _nodes,
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
    const has_traffic_light = view.getInt8(i * CROSSROAD_STRUCT_SIZE + 12) != 0;
    const lat = view.getFloat32(i * CROSSROAD_STRUCT_SIZE + 13);
    const lng = view.getFloat32(i * CROSSROAD_STRUCT_SIZE + 17);

    crossroads.push({
      id: crossroad_id,
      node_id: node_id,
      has_traffic_light: has_traffic_light,
      lat: lat,
      lng: lng,
    });
  }

  return { crossroads: crossroads, size: count * CROSSROAD_STRUCT_SIZE };
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
    waysCount,
    nodes
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
