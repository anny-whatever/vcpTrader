// App.jsx
import React, {
  useState,
  useEffect,
  useContext,
  lazy,
  Suspense,
  useRef,
  useCallback,
} from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import api from "./utils/api";
import { AuthProvider, AuthContext } from "./utils/AuthContext.jsx";
import { DataContext } from "./utils/DataContext.jsx";
import { Toaster, toast } from "sonner";
import { PlayAlertTriggerSound } from "./utils/PlaySound";
import { jwtDecode } from "jwt-decode";
import PnlDrawer from "./components/PnlDrawer"; // Floating P&L Drawer
import { AnimatePresence, motion } from "framer-motion";
import { Box, CircularProgress } from "@mui/material";

// Import our new navbar
import Navbar from "./components/ui/Navbar.jsx";
import NiftyIndexTicker from "./components/NiftyIndexTicker.jsx";

// Lazy-loaded pages
const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const AllPositions = lazy(() => import("./pages/AllPositions.jsx"));
const Screener = lazy(() => import("./pages/Screener.jsx"));
const LoginPage = lazy(() => import("./pages/LoginPage.jsx"));
const Watchlist = lazy(() => import("./pages/Watchlist.jsx"));
const Alerts = lazy(() => import("./pages/Alerts.jsx"));

// Loading fallback for lazy-loaded components
const PageLoader = () => (
  <Box
    sx={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "calc(100vh - 70px)",
      width: "100%",
    }}
  >
    <CircularProgress color="primary" />
  </Box>
);

// Helper function to check if token is expired
const isTokenExpired = (token) => {
  try {
    const decoded = jwtDecode(token);
    return decoded.exp < Date.now() / 1000;
  } catch (error) {
    return true;
  }
};

// ProtectedRoute component: uses AuthContext to decide if the user is logged in.
const ProtectedRoute = ({ children }) => {
  const { token, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (token && isTokenExpired(token)) {
      logout();
      navigate("/login", { replace: true });
    }
  }, [token, logout, navigate]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

// Page transition variants
const pageVariants = {
  initial: {
    opacity: 0,
    y: 10,
  },
  in: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.25, 0.1, 0.25, 1.0],
    },
  },
  out: {
    opacity: 0,
    y: -10,
    transition: {
      duration: 0.2,
    },
  },
};

// A component that wraps the routes and conditionally renders the PnlDrawer
const AppRoutes = () => {
  const location = useLocation();
  const { logout, token } = useContext(AuthContext);
  const { alertMessages } = useContext(DataContext);

  // Get user info from token
  let userName = "User";
  let userRole = "user";

  if (token) {
    try {
      const decoded = jwtDecode(token);
      userName = decoded.sub || "User";
      userRole = decoded.role || "user";
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // If on login page, don't show the navbar
  if (location.pathname === "/login") {
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial="initial"
          animate="in"
          exit="out"
          variants={pageVariants}
        >
          <Routes location={location}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </motion.div>
      </AnimatePresence>
    );
  }

  return (
    <>
      <Box sx={{ position: "sticky", top: 0, zIndex: 1100 }}>
        <Navbar
          onLogout={logout}
          userName={userName}
          userRole={userRole}
          notificationCount={alertMessages?.length || 0}
          alertMessages={alertMessages}
        />
        <NiftyIndexTicker />
      </Box>
      <Box
        component="main"
        sx={{
          p: { xs: 2, md: 3 },
          minHeight: "calc(100vh - 70px - 33px)", // Adjusted for NiftyIndexTicker height
        }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial="initial"
            animate="in"
            exit="out"
            variants={pageVariants}
            style={{ width: "100%" }}
          >
            <Suspense fallback={<PageLoader />}>
              <Routes location={location}>
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
                <Route
                  path="/alerts"
                  element={
                    <ProtectedRoute>
                      <Alerts />
                    </ProtectedRoute>
                  }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </Box>

      {/* Render the PnL drawer on all pages except "/allpositions" */}
      {location.pathname !== "/allpositions" &&
        location.pathname !== "/login" && <PnlDrawer />}
    </>
  );
};

function App() {
  const [liveData, setLiveData] = useState(null);
  const [positions, setPositions] = useState(null);
  const [riskpool, setRiskpool] = useState(null);
  const [historicalTrades, setHistoricalTrades] = useState(null);
  const [priceAlerts, setPriceAlerts] = useState(null);
  const [alertMessages, setAlertMessages] = useState(null);
  const [watchlistAlerts, setWatchlistAlerts] = useState(null);

  // For WebSocket optimization
  const socketRef = useRef(null);
  const tickUpdateTimeoutRef = useRef(null);
  const lastTickUpdateRef = useRef(0);
  const tickQueueRef = useRef([]);
  const dataUpdateInProgressRef = useRef(false);
  const wsMessageQueueRef = useRef([]);
  const processingMessageRef = useRef(false);

  // Configuration for throttling
  const TICK_THROTTLE_MS = 250; // Limit tick updates to once every 250ms
  const BATCH_API_CALLS = true; // Whether to batch API calls
  const WS_MESSAGE_QUEUE_PROCESSING = true; // Process WebSocket messages in a queue

  // Memoize data fetching functions to avoid recreating them on each render
  const fetchPositions = useCallback(async () => {
    try {
      const response = await api.get("/api/data/positions");
      setPositions(response.data || response);
    } catch (error) {
      console.error("Error fetching positions:", error);
    }
  }, []);

  const fetchRiskpool = useCallback(async () => {
    try {
      const response = await api.get("/api/data/riskpool");
      setRiskpool(response.data || response);
    } catch (error) {
      console.error("Error fetching riskpool:", error);
    }
  }, []);

  const fetchHistoricalTrades = useCallback(async () => {
    try {
      const response = await api.get("/api/data/historicaltrades");
      setHistoricalTrades(response.data || response);
    } catch (error) {
      console.error("Error fetching historical trades:", error);
    }
  }, []);

  const fetchPriceAlerts = useCallback(async () => {
    try {
      const response = await api.get("/api/alerts/list");
      setPriceAlerts(response.data || response);
    } catch (error) {
      console.error("Error fetching price alerts:", error);
    }
  }, []);

  const fetchAlertMessages = useCallback(async () => {
    try {
      const response = await api.get("/api/alerts/messages");
      setAlertMessages(response.data || response);
    } catch (error) {
      console.error("Error fetching alert messages:", error);
    }
  }, []);

  // Batch data fetch for all data updates with debouncing
  const fetchAllData = useCallback(async () => {
    if (dataUpdateInProgressRef.current) return;

    dataUpdateInProgressRef.current = true;
    try {
      await Promise.all([
        fetchRiskpool(),
        fetchHistoricalTrades(),
        fetchPositions(),
        fetchPriceAlerts(),
        fetchAlertMessages(),
      ]);
    } catch (error) {
      console.error("Error fetching all data:", error);
    } finally {
      dataUpdateInProgressRef.current = false;
    }
  }, [
    fetchRiskpool,
    fetchHistoricalTrades,
    fetchPositions,
    fetchPriceAlerts,
    fetchAlertMessages,
  ]);

  // Optimized handler for processing tick data
  const processTicks = useCallback((tickData) => {
    // Queue the ticks for processing
    tickQueueRef.current.push(tickData);

    // If we already have a timeout scheduled, don't schedule another one
    if (tickUpdateTimeoutRef.current) return;

    // Schedule tick processing with requestAnimationFrame and setTimeout for throttling
    const now = Date.now();
    const timeSinceLastUpdate = now - lastTickUpdateRef.current;

    if (timeSinceLastUpdate >= TICK_THROTTLE_MS) {
      // It's been long enough since the last update, process immediately
      lastTickUpdateRef.current = now;

      // Use requestAnimationFrame to align with the browser's render cycle
      requestAnimationFrame(() => {
        // Process all queued ticks
        if (tickQueueRef.current.length > 0) {
          // Take only the latest tick data
          const latestTick =
            tickQueueRef.current[tickQueueRef.current.length - 1];

          // Log a debug message specifically for Nifty
          if (
            latestTick &&
            (latestTick[256265] ||
              (Array.isArray(latestTick) &&
                latestTick.some((item) => item.instrument_token === 256265)))
          ) {
            // Removed console.log("Nifty data found in tick update");
          }

          setLiveData(latestTick);
          // Clear the queue
          tickQueueRef.current = [];
        }
      });
    } else {
      // It hasn't been long enough, schedule for later
      const delayTime = TICK_THROTTLE_MS - timeSinceLastUpdate;

      tickUpdateTimeoutRef.current = setTimeout(() => {
        tickUpdateTimeoutRef.current = null;
        lastTickUpdateRef.current = Date.now();

        // Use requestAnimationFrame to align with the browser's render cycle
        requestAnimationFrame(() => {
          // Process all queued ticks
          if (tickQueueRef.current.length > 0) {
            // Take only the latest tick data
            const latestTick =
              tickQueueRef.current[tickQueueRef.current.length - 1];
            setLiveData(latestTick);
            // Clear the queue
            tickQueueRef.current = [];
          }
        });
      }, delayTime);
    }
  }, []);

  // Process WebSocket messages from the queue to prevent blocking the main thread
  const processMessageQueue = useCallback(() => {
    if (
      processingMessageRef.current ||
      wsMessageQueueRef.current.length === 0
    ) {
      return;
    }

    processingMessageRef.current = true;

    // Process a limited number of messages per frame
    const MAX_MESSAGES_PER_BATCH = 5;
    const messagesToProcess = Math.min(
      MAX_MESSAGES_PER_BATCH,
      wsMessageQueueRef.current.length
    );
    const currentBatch = wsMessageQueueRef.current.splice(0, messagesToProcess);

    // Use a zero-timeout to yield to the browser
    setTimeout(() => {
      currentBatch.forEach((message) => {
        try {
          const parsedData = JSON.parse(message);

          // Ignore ping messages immediately
          if (parsedData?.event === "ping") {
            return;
          }

          // Handle different event types more efficiently
          switch (parsedData?.event) {
            case "data_update":
              if (BATCH_API_CALLS) {
                fetchAllData();
              } else {
                Promise.all([
                  fetchRiskpool(),
                  fetchHistoricalTrades(),
                  fetchPositions(),
                  fetchPriceAlerts(),
                  fetchAlertMessages(),
                ]).catch((err) => console.error("Error fetching data:", err));
              }
              break;

            case "live_ticks":
              // Log if Nifty data is present in the incoming message
              if (
                parsedData.data &&
                (parsedData.data[256265] ||
                  (Array.isArray(parsedData.data) &&
                    parsedData.data.some(
                      (item) => item.instrument_token === 256265
                    )))
              ) {
                // Removed console.log("Received Nifty data in WebSocket message");
              }

              // Use our optimized tick processing
              processTicks(parsedData.data);
              break;

            case "alert_update":
              Promise.all([fetchPriceAlerts(), fetchAlertMessages()]).catch(
                (err) => console.error("Error fetching alert data:", err)
              );
              break;

            case "alert_triggered":
              Promise.all([fetchPriceAlerts(), fetchAlertMessages()]).catch(
                (err) => console.error("Error fetching alert data:", err)
              );

              // Schedule sound and toast outside of the current task
              requestAnimationFrame(() => {
                PlayAlertTriggerSound();
                toast.success(
                  parsedData?.message || "Alert triggered successfully",
                  { duration: 15000 }
                );
              });
              break;

            case "watchlist_updated":
              // Use requestAnimationFrame for setting state
              requestAnimationFrame(() => {
                setWatchlistAlerts(parsedData.data);
              });
              break;

            case "echo":
              // Removed console.log("Echo from server:", parsedData.data);
              break;

            default:
            // Removed console.log("Unhandled WebSocket event:", parsedData.event);
          }
        } catch (error) {
          console.error("Error processing WebSocket message:", error);
        }
      });

      processingMessageRef.current = false;

      // If there are more messages, schedule another processing batch
      if (wsMessageQueueRef.current.length > 0) {
        requestAnimationFrame(processMessageQueue);
      }
    }, 0);
  }, [fetchAllData, processTicks, fetchPriceAlerts, fetchAlertMessages]);

  // WebSocket connection setup
  const connectWebSocket = useCallback(() => {
    // Clean up any existing socket
    if (socketRef.current) {
      socketRef.current.close();
    }

    socketRef.current = new WebSocket("wss://api.tradekeep.in/socket/ws");

    socketRef.current.onopen = () => {
      // Removed console.log("Connected to WebSocket");
    };

    socketRef.current.onmessage = (event) => {
      // Always use optimized queue processing for better performance
      if (WS_MESSAGE_QUEUE_PROCESSING) {
        // Push the message to the queue - don't parse immediately
        wsMessageQueueRef.current.push(event.data);

        // Trigger queue processing if not already in progress
        if (!processingMessageRef.current) {
          requestAnimationFrame(processMessageQueue);
        }
      } else {
        // Fallback to optimized direct processing if queue is disabled
        try {
          const parsedData = JSON.parse(event.data);
          
          // Process the message directly using optimized handling
          processWebSocketMessage(parsedData);
          
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
          if (socketRef.current) {
            socketRef.current.close();
          }
          setTimeout(connectWebSocket, 5000);
        }
      }
    };

    socketRef.current.onclose = () => {
      // Removed console.log("WebSocket closed, attempting to reconnect...");
      setTimeout(connectWebSocket, 5000);
    };

    socketRef.current.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [processMessageQueue]);

  // Set up WebSocket connection
  useEffect(() => {
    connectWebSocket();

    // Cleanup function
    return () => {
      // Clear any pending timeouts
      if (tickUpdateTimeoutRef.current) {
        clearTimeout(tickUpdateTimeoutRef.current);
        tickUpdateTimeoutRef.current = null;
      }

      // Close the WebSocket connection
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connectWebSocket]);

  // Initial data fetch on component mount
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  return (
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
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "rgba(39, 39, 42, 0.8)",
              color: "#fff",
              backdropFilter: "blur(8px)",
              borderRadius: "8px",
              boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
            },
          }}
        />
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </DataContext.Provider>
    </AuthProvider>
  );
}

export default App;
