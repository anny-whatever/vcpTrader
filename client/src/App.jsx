// App.jsx
import { useState, useEffect, useContext } from "react";
import { DataContext } from "./utils/DataContext";
import { Routes, Route, BrowserRouter, Navigate } from "react-router-dom";
import Navbar from "./components/NavbarComponent.jsx";

import Dashboard from "./pages/Dashboard.jsx";
import AllPositions from "./pages/AllPositions.jsx";
import Screener from "./pages/Screener.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import api from "./utils/api";
import { AuthProvider, AuthContext } from "./utils/AuthContext.jsx";

// ProtectedRoute component: uses AuthContext to decide if the user is logged in.
const ProtectedRoute = ({ children }) => {
  const { token } = useContext(AuthContext);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  const [liveData, setLiveData] = useState(null);
  const [positions, setPositions] = useState(null);
  const [riskpool, setRiskpool] = useState(null);
  const [historicalTrades, setHistoricalTrades] = useState(null);

  // Establish WebSocket connection using the URL ws://localhost:8000/ws/ws
  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8000/socket/ws");

    socket.onopen = () => {
      console.log("Connected to WebSocket");
    };

    socket.onmessage = (event) => {
      const parsedData = JSON.parse(event?.data);
      if (parsedData?.event === "data_update") {
        fetchRiskpool();
        fetchHistoricalTrades();
        fetchPositions();
      }
      if (parsedData?.event === "live_ticks") {
        setLiveData(parsedData?.data);
      }
    };

    socket.onclose = () => {
      console.log("WebSocket closed");
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // Clean up on component unmount
    return () => {
      socket.close();
    };
  }, []);

  // Data fetching functions (using your axios instance with interceptor)
  const fetchPositions = async () => {
    try {
      const response = await api.get("/api/data/positions");

      setPositions(response);
    } catch (error) {
      console.error("Error fetching positions:", error);
    }
  };

  const fetchRiskpool = async () => {
    try {
      const response = await api.get("/api/data/riskpool");

      setRiskpool(response);
    } catch (error) {
      console.error("Error fetching riskpool:", error);
    }
  };

  const fetchHistoricalTrades = async () => {
    try {
      const response = await api.get("/api/data/historicaltrades");

      setHistoricalTrades(response);
    } catch (error) {
      console.error("Error fetching historical trades:", error);
    }
  };

  // Fetch data on component mount
  useEffect(() => {
    fetchRiskpool();
    fetchHistoricalTrades();
    fetchPositions();
  }, []);

  return (
    <main className="min-h-[100vh] bg-zinc-900">
      <DataContext.Provider
        value={{ liveData, positions, riskpool, historicalTrades }}
      >
        <AuthProvider>
          <BrowserRouter>
            <Navbar />
            <Routes>
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/allpositions"
                element={
                  <ProtectedRoute>
                    <AllPositions />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/screener"
                element={
                  <ProtectedRoute>
                    <Screener />
                  </ProtectedRoute>
                }
              />
              <Route path="/login" element={<LoginPage />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </DataContext.Provider>
    </main>
  );
}

export default App;
