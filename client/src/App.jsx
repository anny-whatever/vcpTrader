import { useState, useEffect } from "react";
import { DataContext } from "./utils/DataContext";
import { Routes, Route, BrowserRouter } from "react-router-dom";
import Navbar from "./components/NavbarComponent.jsx";

import Dashboard from "./pages/Dashboard.jsx";
import AllPositions from "./pages/AllPositions.jsx";
import axios from "axios";

function App() {
  const [liveData, setLiveData] = useState(null);
  const [positions, setPositions] = useState(null);
  const [flags, setFlags] = useState(null);

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
      const response = await axios.get("http://localhost:8000/api/positions");
      console.log(response);
      setPositions(response);
    };

    fetchPositions();
  }, []);

  useEffect(() => {
    const fetchFlags = async () => {
      const response = await axios.get("http://localhost:8000/api/flags");
      console.log(response);
      setFlags(response);
    };

    fetchFlags();
  }, []);

  return (
    <main className="min-h-[100vh] bg-zinc-900">
      <DataContext.Provider value={{ liveData, positions, flags }}>
        <BrowserRouter>
          <Navbar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/allpositions" element={<AllPositions />} />
          </Routes>
        </BrowserRouter>
      </DataContext.Provider>
    </main>
  );
}

export default App;
