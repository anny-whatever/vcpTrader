import { useState, useEffect } from "react";
import { DataContext } from "./utils/DataContext";
import { Routes, Route, BrowserRouter } from "react-router-dom";
import Navbar from "./components/NavbarComponent.jsx";

import Dashboard from "./pages/Dashboard.jsx";
import AllPositions from "./pages/AllPositions.jsx";
import Screener from "./pages/Screener.jsx";
import axios from "axios";

function App() {
  const [liveData, setLiveData] = useState(null);
  const [positions, setPositions] = useState(null);
  const [riskpool, setRiskpool] = useState(null);
  const [historicalTrades, setHistoricalTrades] = useState(null);

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8000/ws/ws"); // Ensure the URL is correct

    socket.onopen = () => {
      console.log("Connected to WebSocket");
    };

    socket.onmessage = (event) => {
      setLiveData(JSON.parse(event.data).data); // Update your state with the incoming data
    };

    socket.onclose = () => {
      console.log("WebSocket closed");
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, []);

  useEffect(() => {
    const fetchPositions = async () => {
      const response = await axios.get(
        "http://localhost:8000/api/data/positions"
      );
      console.log("Position", response);
      setPositions(response);
    };
    const fetchRiskpool = async () => {
      const response = await axios.get(
        "http://localhost:8000/api/data/riskpool"
      );
      console.log(response);
      setRiskpool(response);
    };

    const fetchHistoricalTrades = async () => {
      const response = await axios.get(
        "http://localhost:8000/api/data/historicaltrades"
      );
      console.log(response);
      setHistoricalTrades(response);
    };

    fetchRiskpool();
    fetchHistoricalTrades();
    fetchPositions();
  }, []);

  return (
    <main className="min-h-[100vh] bg-zinc-900">
      <DataContext.Provider
        value={{ liveData, positions, riskpool, historicalTrades }}
      >
        <BrowserRouter>
          <Navbar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/allpositions" element={<AllPositions />} />
            <Route path="/screener" element={<Screener />} />
          </Routes>
        </BrowserRouter>
      </DataContext.Provider>
    </main>
  );
}

export default App;
