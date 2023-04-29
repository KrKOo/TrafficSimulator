import { Icon, LatLngExpression } from 'leaflet';
import React, { useEffect, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Circle,
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
  coords: LatLng;
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
      coords: event.coords,
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

const getCarPropsAtTime = (car_props_in_time: CarProps[], time: number) => {
  if (time < car_props_in_time[0].time) {
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

  let coords: LatLng;
  if (prev_event_props.lane !== next_event_props.lane) {
    // position = prev_event_props.lane.is_forward ? 100 : 0;
    coords = next_event_props.coords;
  } else {
    const lat_diff = next_event_props.coords.lat - prev_event_props.coords.lat;
    const lng_diff = next_event_props.coords.lng - prev_event_props.coords.lng;

    // const position_diff = next_event_props.position - prev_event_props.position;

    const time_fraction = (time - prev_event_props.time) / time_diff;

    coords = {
      lat: prev_event_props.coords.lat + time_fraction * lat_diff,
      lng: prev_event_props.coords.lng + time_fraction * lng_diff,
    };
  }

  if (!coords) {
    //TODO: refactor
    console.log('no coords', prev_event_props.id);
    return null;
  }

  return {
    id: prev_event_props.id,
    time: time,
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

    const carProps = getCarPropsInTime(simulation.events, Infinity);
    console.log(carProps);
    setCarPropsInTime(carProps);
  }, [simulation]);

  return (
    <MapContainer center={position} zoom={13} scrollWheelZoom={true}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
      />
      {lanes.map((lane, key) => {
        return <Polyline key={key} positions={lane} dashOffset='50' />;
      })}

      {simulation?.crossroads.map((crossroad, key) => {
        return (
          crossroad.has_traffic_light && (
            <Circle
              center={{ lat: crossroad.lat, lng: crossroad.lng }}
              color='red'
              fillColor='green'
              radius={10}
            />
          )
        );
      })}

      {cars?.map((car, key) => {
        return (
          car.coords && (
            <Marker
              key={key}
              position={car.coords}
              // icon={
              //   new Icon({
              //     iconUrl:
              //       car.id == 561
              //         ? 'https://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|2ecc71&chf=a,s,ee00FFFF'
              //         : 'https://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|abcdef&chf=a,s,ee00FFFF',
              //   })
              // }
            >
              <Popup>
                <div>id: {car.id}</div>
                <div>lane_id: {car.lane.id}</div>
                <div>speed: {car.speed}</div>
              </Popup>
            </Marker>
          )
          // <Circle
          //   key={key}
          //   center={car.coords}
          //   color='green'
          //   fillColor='green'
          //   radius={2}></Circle>
        );
      })}
    </MapContainer>
  );
};

export default Map;
