import { Icon, LatLngExpression } from 'leaflet';
import React, { useEffect, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  Polyline,
} from 'react-leaflet';
import { Simulation, Way, Lane, Event, LatLng, Crossroad } from 'types/roadnet';
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
  way?: Way;
  crossroad?: Crossroad;
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
      crossroad: event.crossroad,
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
  lane: Lane,
  position: number,
  is_forward: boolean
) => {
  const nodes = is_forward ? lane.nodes : [...lane.nodes].reverse();
  const precision = 0.001;

  let position_in_km = (position * lane.length) / 100;

  for (let i = 0; i < nodes.length - 1; i++) {
    const node = nodes[i];
    const nextNode = nodes[i + 1];
    const distance = haversine(node, nextNode);

    if (!distance) return node;

    if (position_in_km - distance <= precision) {
      const lat =
        node.lat + (nextNode.lat - node.lat) * (position_in_km / distance);
      const lng =
        node.lng + (nextNode.lng - node.lng) * (position_in_km / distance);

      return { lat: lat, lng: lng };
    }
    position_in_km -= distance;
  }

  return null;
};

const getCarPropsAtTime = (car_props_in_time: CarProps[], time: number) => {
  if (
    time < car_props_in_time[0].time ||
    time > car_props_in_time[car_props_in_time.length - 1].time
  ) {
    return null;
  }

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
    prev_event_props.lane,
    position,
    prev_event_props.lane.is_forward
  );

  if (!coords) {
    console.log('no coords', prev_event_props.id);
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
  const [cars, setCars] = useState<CarProps[]>();
  const [carPropsInTime, setCarPropsInTime] = useState<
    Record<number, CarProps[]>
  >({});

  useEffect(() => {
    setTime(time_prop);

    const cars_props: CarProps[] = [];
    for (const [key, value] of Object.entries(carPropsInTime)) {
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
    const carProps = getCarPropsInTime(simulation.events, Infinity);
    console.log(carProps);
    setCarPropsInTime(carProps);
  }, [simulation]);

  return (
    <MapContainer
      center={position}
      zoom={13}
      scrollWheelZoom={true}
      maxZoom={25}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
      />

      {cars?.map((car, key) => {
        if (!car.coords) return null;

        return (
          <Circle
            key={key}
            center={car.coords}
            color='blue'
            fillColor='lightblue'
            radius={1.5}>
            <Popup>
              <div>id: {car.id}</div>
              <div>lane_id: {car.lane.id}</div>
              <div>speed: {car.speed}</div>
            </Popup>
          </Circle>
        );
      })}

      {simulation && <Roadnet simulation={simulation} />}
    </MapContainer>
  );
};

interface RoadnetProps {
  simulation: Simulation;
}

const Roadnet = React.memo(({ simulation }: RoadnetProps) => {
  const [lanes, setLanes] = useState<Lane[][]>([]);
  useEffect(() => {
    if (!simulation) return;

    const lanes = simulation.ways.map((way) => {
      return way.lanes;
    });

    setLanes(lanes);
  }, [simulation]);
  return (
    <>
      {lanes.map((way_lanes) => {
        return way_lanes.map((lane, key) => (
          <Polyline
            key={key}
            positions={lane.nodes}
            dashOffset='50'
            color={lane.is_forward ? 'red' : 'green'}
            weight={2}
          />
        ));
      })}

      {simulation?.crossroads.map((crossroad, key) => {
        return (
          <>
            {/* {crossroad.has_traffic_light && (
              <Circle
                center={{ lat: crossroad.lat, lng: crossroad.lng }}
                color='red'
                fillColor='green'
                radius={10}
              />
            )} */}

            {crossroad.lanes.map((lane, key) => {
              return (
                <Polyline
                  key={key}
                  positions={lane.nodes}
                  dashOffset='50'
                  color={'gray'}
                  weight={1}
                />
              );
            })}
          </>
        );
      })}
    </>
  );
});

export default Map;
