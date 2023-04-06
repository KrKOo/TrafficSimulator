import { LatLngExpression } from 'leaflet';
import React, { useEffect, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
} from 'react-leaflet';
import { Simulation, Way, Lane, Event, LatLng } from 'types/roadnet';
import { haversine } from 'utils/math';

interface MapProps {
  simulation?: Simulation;
  time: number;
}

interface CarProps {
  id: number;
  time: number;
  position: number;
  coords?: LatLng;
  way: Way;
  lane: Lane;
  speed: number;
}

const getCarPropsInTime = (events: Event[], max_time: number) => {
  const car_props_at_time: Record<number, CarProps[]> = {};

  events.forEach((event) => {
    if (!car_props_at_time[event.car_id]) {
      car_props_at_time[event.car_id] = [];
    }

    car_props_at_time[event.car_id].push({
      id: event.car_id,
      time: event.time,
      position: event.position,
      way: event.way,
      lane: event.lane,
      speed: event.speed,
    });

    if (event.time > max_time) {
      return;
    }
  });

  return car_props_at_time;
};

const getCoordsFromPosition = (
  way: Way,
  lane: Lane,
  position: number,
  is_forward: boolean
) => {
  const nodes = is_forward ? way.nodes : [...way.nodes].reverse();
  const precision = 0.001;

  let position_in_km = (position * lane.length) / 100;

  for (let i = 0; i < nodes.length - 1; i++) {
    const node = nodes[i];
    const nextNode = nodes[i + 1];
    const distance = haversine(node, nextNode);
    if (position_in_km - distance <= precision) {
      const lat =
        node.lat + (nextNode.lat - node.lat) * (position_in_km / distance);
      const lng =
        node.lng + (nextNode.lng - node.lng) * (position_in_km / distance);

      return { lat, lng };
    }
    position_in_km -= distance;
  }

  return null;
};

const getCarPropsAtTime = (car_props_in_time: CarProps[], time: number) => {
  const next_event_index = car_props_in_time.findIndex(
    (props_at_time) => props_at_time.time >= time
  );

  if (next_event_index === -1) {
    return car_props_in_time[car_props_in_time.length - 1];
  } else if (next_event_index === 0) {
    return car_props_in_time[0];
  }

  const prev_event_props = car_props_in_time[next_event_index - 1];
  const next_event_props = car_props_in_time[next_event_index];

  const time_diff = next_event_props.time - prev_event_props.time;

  let position;
  if (prev_event_props.lane !== next_event_props.lane) {
    // position = prev_event_props.lane.is_forward ? 100 : 0;
    position = 100;
  } else {
    const position_diff = next_event_props.position - prev_event_props.position;

    position =
      prev_event_props.position +
      ((time - prev_event_props.time) / time_diff) * position_diff;
  }

  const coords = getCoordsFromPosition(
    prev_event_props.way,
    prev_event_props.lane,
    position,
    prev_event_props.lane.is_forward
  );

  if (!coords) {
    //TODO: refactor
    console.log('no coords');
    return null;
  }

  return {
    id: prev_event_props.id,
    time: time,
    position: position,
    coords: coords,
    way: prev_event_props.way,
    lane: prev_event_props.lane,
    speed: prev_event_props.speed,
  };
};

const Map = ({ simulation, time: time_prop }: MapProps) => {
  const position = { lat: 49.2335, lng: 16.5765 };
  const [time, setTime] = useState<number>(0);
  const [ways, setWays] = useState<Way[]>([]);
  const [lanes, setLanes] = useState<LatLngExpression[][]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [cars, setCars] = useState<CarProps[]>();

  useEffect(() => {
    setTime(time_prop);

    const car_props_in_time = getCarPropsInTime(events, time);

    const cars_props: CarProps[] = [];
    for (const [key, value] of Object.entries(car_props_in_time)) {
      const car_props = getCarPropsAtTime(value, time);
      if (!car_props) {
        continue;
      }
      cars_props.push(car_props);
    }

    setCars(cars_props);
  }, [time_prop]);

  useEffect(() => {
    if (!simulation) return;
    setWays(simulation.ways);

    const lanes = simulation.ways.map((way) => {
      const lines = [];

      for (let i = 0; i < way.nodes.length - 1; i++) {
        const node = way.nodes[i];
        const nextNode = way.nodes[i + 1];
        lines.push(
          { lat: node.lat, lng: node.lng },
          { lat: nextNode.lat, lng: nextNode.lng }
        );
      }

      return lines;
    });

    setLanes(lanes);
    setEvents(simulation.events);
  }, [simulation]);

  return (
    <MapContainer center={position} zoom={13} scrollWheelZoom={true}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
      />
      {lanes.map((lane, key) => {
        return <Polyline key={key} positions={lane} />;
      })}

      {cars?.map((car, key) => {
        return (
          car.coords && (
            <Marker key={key} position={car.coords}>
              <Popup>
                <div>Car {car.id}</div>
                <div>Speed: {car.speed}</div>
              </Popup>
            </Marker>
          )
        );
      })}
    </MapContainer>
  );
};

export default Map;
