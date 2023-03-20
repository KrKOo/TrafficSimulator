import { useEffect, useState } from 'react';
import reactLogo from './assets/react.svg';
import viteLogo from '/vite.svg';
import './App.css';

const STRUCT_SIZE = 6 * 4;

interface Event {
  time: number;
  car_id: number;
  way_id: number;
  lane_id: number;
  position: number;
  speed: number;
}

const arrayBufferParse = (buffer: ArrayBuffer) => {
  const view = new DataView(buffer);

  const res: Event[] = [];

  for (let i = 0; i < buffer.byteLength; i += STRUCT_SIZE) {
    const time = view.getFloat32(i);
    const car_id = view.getInt32(i + 4);
    const way_id = view.getInt32(i + 8);
    const lane_id = view.getInt32(i + 12);
    const position = view.getFloat32(i + 16);
    const speed = view.getFloat32(i + 20);

    res.push({
      time: time,
      car_id: car_id,
      way_id: way_id,
      lane_id: lane_id,
      position: position,
      speed: speed,
    });
  }

  return res;
};

const App = () => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    (async () => {
      const res = await fetch('http://127.0.0.1:5000/');
      const data = arrayBufferParse(await res.arrayBuffer());
      console.log(data);
    })();
  }, []);

  return <div className='App'>HELLO WORLD</div>;
};

export default App;
