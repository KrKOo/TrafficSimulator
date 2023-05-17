import React, { useEffect, useState } from 'react';
import { Circle, Polyline, Popup } from 'react-leaflet';
import { Lane, Simulation } from 'types/entities';

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
            weight={2}>
            <Popup>
              <div>id: {lane.id}</div>
            </Popup>
          </Polyline>
        ));
      })}

      {simulation?.crossroads.map((crossroad, key) => {
        return (
          <>
            {crossroad.has_traffic_light && (
              <Circle
                center={{ lat: crossroad.lat, lng: crossroad.lng }}
                color='red'
                fillColor='green'
                radius={15}
              />
            )}

            {crossroad.lanes.map((lane, key) => {
              return (
                <Polyline
                  key={key}
                  positions={lane.nodes}
                  dashOffset='50'
                  color={'gray'}
                  weight={1}>
                  <Popup>
                    <div>id: {lane.id}</div>
                  </Popup>
                </Polyline>
              );
            })}
          </>
        );
      })}
    </>
  );
});

export default Roadnet;
