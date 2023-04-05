import { useEffect, useState } from 'react';
import './App.css';
import parseSimulation from 'modules/parser';

const App = () => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    (async () => {
      const res = await fetch('http://127.0.0.1:5000/');
      const data = parseSimulation(await res.arrayBuffer());
      console.log(data);
    })();
  }, []);

  return <div className='App'>HELLO WORLD</div>;
};

export default App;
