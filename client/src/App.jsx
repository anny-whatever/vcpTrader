import React, { useState, useEffect, useContext, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/NavbarComponent.jsx";
import api from "./utils/api";
import { AuthProvider, AuthContext } from "./utils/AuthContext.jsx";
import { DataContext } from "./utils/DataContext.jsx";
import { Toaster, toast } from "sonner";
import { PlayAlertTriggerSound } from "./utils/PlaySound";

// Lazy-loaded pages
const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const AllPositions = lazy(() => import("./pages/AllPositions.jsx"));
const Screener = lazy(() => import("./pages/Screener.jsx"));
const LoginPage = lazy(() => import("./pages/LoginPage.jsx"));
const Watchlist = lazy(() => import("./pages/Watchlist.jsx"));

// Helper function to check if token is expired
const isTokenExpired = (token) => {
  try {
    const decoded = jwt_decode(token);
    // 'exp' is in seconds, so compare with current time in seconds
    return decoded.exp < Date.now() / 1000;
  } catch (error) {
    // If there's an error decoding, consider the token invalid/expired
    return true;
  }
};

// ProtectedRoute component: uses AuthContext to decide if the user is logged in.
const ProtectedRoute = ({ children }) => {
  const { token, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (token && isTokenExpired(token)) {
      // Optionally, clear the token using a logout method
      logout();
      // Redirect to login if the token is expired
      navigate("/login", { replace: true });
    }
  }, [token, logout, navigate]);

  // If no token exists, redirect immediately
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
  const [priceAlerts, setPriceAlerts] = useState(null);
  const [alertMessages, setAlertMessages] = useState(null);
  const [watchlistAlerts, setWatchlistAlerts] = useState(null);
  const { token } = useContext(AuthContext);

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

          // Ignore ping messages
          if (parsedData?.event === "ping") {
            return;
          }

          if (parsedData?.event === "data_update") {
            fetchRiskpool();
            fetchHistoricalTrades();
            fetchPositions();
            fetchPriceAlerts();
            fetchAlertMessages();
          }
          if (parsedData?.event === "live_ticks") {
            setLiveData(parsedData.data);
          }
          if (parsedData?.event === "alert_update") {
            fetchPriceAlerts();
            fetchAlertMessages();
            console.log("Alert updated");
          }
          if (parsedData?.event === "alert_triggered") {
            fetchPriceAlerts();
            fetchAlertMessages();
            PlayAlertTriggerSound();
            toast.success(
              parsedData?.message || "Alert triggered successfully",
              {
                duration: 15000,
              }
            );
          }
          if (parsedData?.event === "watchlist_updated") {
            setWatchlistAlerts(parsedData.data);
          }
          // Optionally handle echo messages
          if (parsedData?.event === "echo") {
            console.log("Echo from server:", parsedData.data);
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
          socket.close();
          setTimeout(connect, 5000);
        }
      };

      socket.onclose = () => {
        console.log("WebSocket closed, attempting to reconnect...");
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

  // Data fetching functions
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

  const fetchPriceAlerts = async () => {
    try {
      const response = await api.get("/api/alerts/list");
      setPriceAlerts(response.data || response);
    } catch (error) {
      console.error("Error fetching price alerts:", error);
    }
  };

  const fetchAlertMessages = async () => {
    try {
      const response = await api.get("/api/alerts/messages");
      setAlertMessages(response.data || response);
    } catch (error) {
      console.error("Error fetching alert messages:", error);
    }
  };

  // Fetch all data on component mount
  useEffect(() => {
    fetchRiskpool();
    fetchHistoricalTrades();
    fetchPositions();
    fetchPriceAlerts();
    fetchAlertMessages();
  }, []);

  return (
    <div className="min-h-[100vh] bg-zinc-900">
      <Toaster position="bottom-right" />
      <AuthProvider>
        <DataContext.Provider
          value={{
            liveData,
            positions,
            riskpool,
            historicalTrades,
            priceAlerts,
            alertMessages,
            watchlistAlerts,
          }}
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
              <Route
                path="/watchlist"
                element={
                  <ProtectedRoute>
                    <Watchlist />
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
