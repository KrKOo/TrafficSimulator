import { useEffect, useRef, useState } from 'react';
import './App.css';
import parseSimulation from 'modules/parser';
import Map from 'components/Map';
import { Simulation } from 'types/entities';
import Slider from 'react-slider';

const App = () => {
  const [simulation, setSimulation] = useState<Simulation>();
  const [endTime, setEndTime] = useState(0);
  const [sliderTime, setSliderTime] = useState(0);
  const [vehicleCount, setVehicleCount] = useState(10);
  const [timeSpan, setTimeSpan] = useState(100);
  const [simulationSeed, setSimulationSeed] = useState(
    Math.floor(Math.random() * 10000)
  );

  const [simulationState, setSimulationState] = useState('');
  const intervalRef = useRef<number>();

  useEffect(() => {
    if (!simulation) {
      return;
    }

    startTimer();
  }, [simulation]);

  const startTimer = () => {
    if (intervalRef.current) {
      return;
    }

    intervalRef.current = window.setInterval(() => {
      setSliderTime((prevTime) => {
        if (prevTime >= endTime) {
          stopTimer();
          return endTime;
        }
        return prevTime + 0.1;
      });
    }, 100);
  };

  const stopTimer = () => {
    window.clearInterval(intervalRef.current);
    intervalRef.current = undefined;
  };

  const fetchSimulation = async () => {
    setSliderTime(0);
    stopTimer();

    setSimulationState('Simulating...');
    const res = await fetch(
      'http://127.0.0.1:5000' +
        `?vehicle_count=${vehicleCount} + &time_span=${timeSpan} + &seed=${simulationSeed}`
    );

    setSimulationState('Parsing results...');
    const arrayBuffer = await res.arrayBuffer();

    const data = parseSimulation(arrayBuffer);

    setSimulation(data);

    const end_time = data.car_events[data.car_events.length - 1].time;
    setEndTime(end_time);

    setSimulationState('');
  };

  const handleSliderChange = (value: number) => {
    setSliderTime(value);
  };

  return (
    <div className='App' style={{ width: '100vw', height: '100vh' }}>
      <div style={{ height: '90vh', width: '100vw' }}>
        <Map simulation={simulation} time={sliderTime} />
      </div>
      <div style={{ height: '10vh' }}>
        <div
          style={{
            display: 'flex',
            flexDirection: 'row',
            width: '95%',
            margin: 'auto',
            alignItems: 'center',
          }}>
          <div
            className='input-container'
            style={{
              display: 'flex',
              flexDirection: 'column',
              padding: '5px',
            }}>
            <label htmlFor='vehicle_count'>Vehicle count</label>
            <input
              id='vehicle_count'
              type='number'
              placeholder='Vehicle count'
              value={vehicleCount}
              onChange={(e) => setVehicleCount(parseInt(e.target.value))}
            />
          </div>

          <div
            className='input-container'
            style={{
              display: 'flex',
              flexDirection: 'column',
              padding: '5px',
            }}>
            <label htmlFor='time_span'>Time span [s]</label>
            <input
              type='number'
              placeholder='Time span'
              value={timeSpan}
              onChange={(e) => setTimeSpan(parseInt(e.target.value))}
            />
          </div>

          <div
            className='input-container'
            style={{
              display: 'flex',
              flexDirection: 'column',
              padding: '5px',
            }}>
            <label htmlFor='seed'>Seed</label>
            <input
              type='number'
              placeholder='Seed'
              value={simulationSeed}
              onChange={(e) => setSimulationSeed(parseInt(e.target.value))}
            />
          </div>

          <div>
            <button className='control-button' onClick={fetchSimulation}>
              Fetch simulation
            </button>
            <button className='control-button' onClick={startTimer}>
              Play
            </button>
            <button className='control-button' onClick={stopTimer}>
              Pause
            </button>
          </div>
          <h3 style={{ margin: 'auto' }}>{sliderTime.toFixed(2)}s</h3>

          <h3 style={{ margin: 'auto' }}>{simulationState}</h3>
        </div>
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
