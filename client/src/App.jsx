// App.jsx
import React from "react";
import { useState, useEffect, useContext, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/NavbarComponent.jsx";
import api from "./utils/api";
import { AuthProvider, AuthContext } from "./utils/AuthContext.jsx";
import { DataContext } from "./utils/DataContext.jsx";
import { jwtDecode } from "jwt-decode"; // ✅ Correct import

const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const AllPositions = lazy(() => import("./pages/AllPositions.jsx"));
const Screener = lazy(() => import("./pages/Screener.jsx"));
const LoginPage = lazy(() => import("./pages/LoginPage.jsx"));

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
  const { token, logout } = useContext(AuthContext);

  useEffect(() => {
    let socket;

    const connect = () => {
      socket = new WebSocket("wss://api.devstatz.com/socket/ws");

      socket.onopen = () => {
        console.log("Connected to WebSocket");
      };

      socket.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          if (parsedData?.event === "data_update") {
            fetchRiskpool();
            fetchHistoricalTrades();
            fetchPositions();
          }
          if (parsedData?.event === "live_ticks") {
            setLiveData(parsedData.data);
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      socket.onclose = () => {
        console.log("WebSocket closed, attempting to reconnect...");
        // Optionally, you can use a timeout to reconnect after a delay
        setTimeout(connect, 5000);
      };

      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    };

    connect();

    // Clean up on component unmount
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, []);

  // Data fetching functions (using your axios instance)
  const fetchPositions = async () => {
    try {
      const response = await api.get("/api/data/positions");
      setPositions(response.data || response);
    } catch (error) {
      console.error("Error fetching positions:", error);
    }
  };

  const fetchRiskpool = async () => {
    try {
      const response = await api.get("/api/data/riskpool");
      setRiskpool(response.data || response);
    } catch (error) {
      console.error("Error fetching riskpool:", error);
    }
  };

  const fetchHistoricalTrades = async () => {
    try {
      const response = await api.get("/api/data/historicaltrades");
      setHistoricalTrades(response.data || response);
    } catch (error) {
      console.error("Error fetching historical trades:", error);
    }
  };

  // Fetch data on component mount
  useEffect(() => {
    try {
      fetchRiskpool();
      fetchHistoricalTrades();
      fetchPositions();
    } catch (error) {
      console.error("Please Login");
    }
  }, []);

  return (
    <div className=" min-h-[100vh] bg-zinc-900">
      <AuthProvider>
        <DataContext.Provider
          value={{ liveData, positions, riskpool, historicalTrades }}
        >
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
        </DataContext.Provider>
      </AuthProvider>
    </div>
  );
}

export default App;
