import { useEffect, useState } from 'react';
import './App.css';
import parseSimulation from 'modules/parser';
import Map from 'components/Map';
import { Simulation } from 'types/roadnet';
import Slider from 'react-slider';

const App = () => {
  const [simulation, setSimulation] = useState<Simulation>();
  const [endTime, setEndTime] = useState(0);
  const [sliderTime, setSliderTime] = useState(0);

  useEffect(() => {
    (async () => {
      const res = await fetch('http://127.0.0.1:5000/');
      console.log('data fetched');

      const arrayBuffer = await res.arrayBuffer();

      console.log('parsing data');
      const data = parseSimulation(arrayBuffer);
      console.log('data parsed');

      setSimulation(data);
      console.log(data);

      const end_time = data.events[data.events.length - 1].time;
      setEndTime(end_time);
    })();

    const interval = setInterval(() => {
      setSliderTime((seconds) => seconds + 0.1);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  const handleSliderChange = (value: number) => {
    setSliderTime(value);
  };

  return (
    <div className='App' style={{ width: '100vw', height: '100vh' }}>
      <div style={{ height: '90vh', width: '100vw' }}>
        <Map simulation={simulation} time={sliderTime} />
      </div>
      <div style={{ height: '10vh' }}>
        <h3>{sliderTime}</h3>
        <Slider
          min={0}
          max={endTime}
          onChange={handleSliderChange}
          value={sliderTime}
          className='horizontal-slider'
          thumbClassName='example-thumb'
          trackClassName='example-track'
        />
      </div>
    </div>
  );
};

export default App;
