import React, { useContext, useState, useEffect, useRef, useMemo } from "react";
import { DataContext } from "../utils/DataContext";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Paper,
  Chip as MuiChip,
  IconButton,
  Button as MuiButton,
  Divider,
  Card,
  Alert,
  useTheme,
  alpha,
} from "@mui/material";
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button as NextUIButton,
  ButtonGroup,
  Chip,
  Spinner,
} from "@nextui-org/react";
import DeleteIcon from "@mui/icons-material/Delete";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import { Toaster, toast } from "sonner";
import api from "../utils/api";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";
import ChartModal from "../components/ChartModal";

export default function Alerts() {
  const { priceAlerts, liveData } = useContext(DataContext);
  const { token } = useContext(AuthContext);
  const navigate = useNavigate();
  const theme = useTheme();

  const [deletingId, setDeletingId] = useState(null);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [cachedPrices, setCachedPrices] = useState({});
  
  // Determine if user is admin
  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token);
      userRole = decoded.role || "";
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // Update cached prices when liveData changes
  useEffect(() => {
    if (liveData && priceAlerts) {
      // Create a new object to avoid direct state mutation
      const newCachedPrices = { ...cachedPrices };

      // Update only the prices that have changed in liveData
      liveData.forEach((tickData) => {
        if (tickData && tickData.instrument_token) {
          newCachedPrices[tickData.instrument_token] = tickData.last_price;
        }
      });

      // Only update state if there are changes
      if (Object.keys(newCachedPrices).length > 0) {
        setCachedPrices((prev) => ({ ...prev, ...newCachedPrices }));
      }
    }
  }, [liveData]);

  // Initialize cached prices when priceAlerts change
  useEffect(() => {
    if (priceAlerts && liveData) {
      const newCachedPrices = { ...cachedPrices };

      // Try to get initial prices from liveData
      priceAlerts.forEach((alert) => {
        const tickData = liveData.find(
          (tick) => tick.instrument_token === alert.instrument_token
        );

        if (tickData && tickData.last_price) {
          newCachedPrices[alert.instrument_token] = tickData.last_price;
        }
      });

      setCachedPrices((prev) => ({ ...prev, ...newCachedPrices }));
    }
  }, [priceAlerts]);

  // Get current price from cached prices instead of direct liveData lookup
  const getCurrentPrice = (instrumentToken) => {
    return cachedPrices[instrumentToken] || null;
  };

  // Calculate percentage difference
  const calculateDifference = (alertPrice, currentPrice) => {
    if (!currentPrice) return null;

    const difference = ((currentPrice - alertPrice) / alertPrice) * 100;
    return difference.toFixed(2);
  };

  // Handle delete alert
  const handleDeleteAlert = async (alertId) => {
    try {
      setDeletingId(alertId);
      await api.delete("/api/alerts/remove", { params: { alert_id: alertId } });
      PlayToastSound();
      toast.success("Alert removed successfully", {
        duration: 5000,
      });
    } catch (error) {
      PlayErrorSound();
      toast.error("Failed to delete alert", {
        duration: 5000,
      });
      console.error("Error deleting alert:", error);
    } finally {
      setDeletingId(null);
    }
  };

  // Chart modal handlers
  const handleOpenChartModal = () => setIsChartModalOpen(true);
  const handleCloseChartModal = () => setIsChartModalOpen(false);

  // Open chart modal with the symbol and token
  const openChartModal = (symbol, instrumentToken) => {
    setChartData({
      symbol: symbol,
      token: instrumentToken,
    });
    handleOpenChartModal();
  };

  // Memoize rendering of table rows to prevent forced reflows
  const renderTableRows = useMemo(() => {
    if (!priceAlerts) return null;

    return priceAlerts.map((alert) => {
      const currentPrice = getCurrentPrice(alert.instrument_token);
      const difference = calculateDifference(alert.price, currentPrice);
      const differenceClass = parseFloat(difference) >= 0 ? "text-green-500" : "text-red-500";

      return (
        <TableRow key={alert.id}>
          <TableCell>{alert.symbol}</TableCell>
          <TableCell>
            <Chip
              size="sm"
              color={alert.alert_type === "sl" ? "danger" : "success"}
              variant="flat"
              classNames={{
                base: `px-2 py-1 ${alert.alert_type === "sl" ? "bg-red-500/20" : "bg-green-500/20"}`,
                content: `text-xs font-medium ${alert.alert_type === "sl" ? "text-red-500" : "text-green-500"}`,
              }}
            >
              {alert.alert_type === "sl" ? "Stop Loss" : "Target"}
            </Chip>
          </TableCell>
          <TableCell>₹{alert.price.toFixed(2)}</TableCell>
          <TableCell>
            {currentPrice ? (
              <span className="font-medium">₹{currentPrice.toFixed(2)}</span>
            ) : (
              <span className="text-zinc-400">--</span>
            )}
          </TableCell>
          <TableCell>
            {difference ? (
              <Chip
                size="sm"
                color={parseFloat(difference) >= 0 ? "success" : "danger"}
                variant="flat"
                classNames={{
                  base: `px-2 py-1 ${parseFloat(difference) >= 0 ? "bg-green-500/20" : "bg-red-500/20"}`,
                  content: `text-xs font-medium ${parseFloat(difference) >= 0 ? "text-green-500" : "text-red-500"}`,
                }}
              >
                {difference}%
              </Chip>
            ) : (
              <span className="text-zinc-400">--</span>
            )}
          </TableCell>
          <TableCell>
            <ButtonGroup size="sm" variant="flat" className="rounded-lg">
              <NextUIButton
                color="warning"
                variant="flat"
                className="min-w-[40px] h-9 bg-amber-500/20 hover:bg-amber-500/30 text-amber-500"
                onPress={() => openChartModal(alert.symbol, alert.instrument_token)}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="w-5 h-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                  />
                </svg>
              </NextUIButton>
              {userRole === "admin" && (
                <NextUIButton
                  color="danger"
                  variant="flat"
                  className="min-w-[40px] h-9 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                  onPress={() => handleDeleteAlert(alert.id)}
                  isDisabled={deletingId === alert.id}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="w-5 h-5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" 
                    />
                  </svg>
                </NextUIButton>
              )}
            </ButtonGroup>
          </TableCell>
        </TableRow>
      );
    });
  }, [priceAlerts, cachedPrices, userRole, deletingId]);

  // Memoize mobile card rendering
  const renderMobileCards = useMemo(() => {
    if (!priceAlerts) return null;

    return priceAlerts.map((alert) => {
      const currentPrice = getCurrentPrice(alert.instrument_token);
      const difference = calculateDifference(alert.price, currentPrice);
      const differenceClass = parseFloat(difference) >= 0 ? "text-green-500" : "text-red-500";

      return (
        <div
          key={`${alert.id}-mobile`}
          className="flex flex-col gap-3 p-5 bg-zinc-900/80 backdrop-blur-sm rounded-xl border border-zinc-800/70 shadow-md transition-all hover:border-zinc-700 hover:bg-zinc-800/80"
        >
          <div className="flex items-center justify-between">
            <span className="text-base font-bold text-white">{alert.symbol}</span>
            <Chip
              size="sm"
              color={alert.alert_type === "sl" ? "danger" : "success"}
              variant="flat"
              classNames={{
                base: `px-2 py-1 ${alert.alert_type === "sl" ? "bg-red-500/10" : "bg-green-500/10"}`,
                content: `text-xs font-medium ${alert.alert_type === "sl" ? "text-red-500" : "text-green-500"}`,
              }}
            >
              {alert.alert_type === "sl" ? "Stop Loss" : "Target"}
            </Chip>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mt-1">
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Alert Price
              </span>
              <span className="text-sm font-medium text-white">
                ₹{alert.price.toFixed(2)}
              </span>
            </div>
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Current Price
              </span>
              <span className="text-sm font-medium text-white">
                {currentPrice ? `₹${currentPrice.toFixed(2)}` : "--"}
              </span>
            </div>
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Difference
              </span>
              {difference ? (
                <span className={`text-sm font-medium ${differenceClass}`}>
                  {difference}%
                </span>
              ) : (
                <span className="text-sm font-medium text-zinc-400">--</span>
              )}
            </div>
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Actions
              </span>
              <div className="flex mt-1">
                <ButtonGroup className="shadow-sm gap-1 flex flex-wrap">
                  <NextUIButton
                    size="sm"
                    color="warning"
                    variant="flat"
                    className="min-w-[28px] w-7 h-7 p-0 bg-amber-500/20 hover:bg-amber-500/30 text-amber-500"
                    onPress={() => openChartModal(alert.symbol, alert.instrument_token)}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-3.5 h-3.5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                      />
                    </svg>
                  </NextUIButton>
                  {userRole === "admin" && (
                    <NextUIButton
                      size="sm"
                      color="danger"
                      variant="flat"
                      className="min-w-[28px] w-7 h-7 p-0 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                      onPress={() => handleDeleteAlert(alert.id)}
                      isDisabled={deletingId === alert.id}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-3.5 h-3.5"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" 
                        />
                      </svg>
                    </NextUIButton>
                  )}
                </ButtonGroup>
              </div>
            </div>
          </div>
        </div>
      );
    });
  }, [priceAlerts, cachedPrices, userRole, deletingId]);

  if (!priceAlerts || priceAlerts.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ mb: 3 }}>
          Price Alerts
        </Typography>
        <Card
          sx={{
            p: 4,
            textAlign: "center",
            backgroundColor: alpha(theme.palette.background.paper, 0.7),
          }}
        >
          <Box sx={{ mb: 2 }}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="64"
              height="64"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ margin: "0 auto" }}
            >
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
          </Box>
          <Typography variant="h6" sx={{ mb: 1 }}>
            No Price Alerts
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            You haven't set any price alerts yet. Add alerts from the watchlist
            to get notified when a stock reaches your target price.
          </Typography>
          <MuiButton
            variant="outlined"
            color="primary"
            onClick={() => navigate("/watchlist")}
          >
            Go to Watchlist
          </MuiButton>
        </Card>
      </Box>
    );
  }

  return (
    <div className="w-full px-6 text-white">
      {/* Chart Modal */}
      <ChartModal
        isOpen={isChartModalOpen}
        onClose={handleCloseChartModal}
        symbol={chartData?.symbol}
        token={chartData?.token}
      />

      <Typography variant="h4" sx={{ mb: 3 }}>
        Price Alerts
      </Typography>

      {/* Desktop Table */}
      <div className="hidden w-full md:block">
        <Table
          aria-label="Alerts table"
          className="w-full no-scrollbar"
          align="center"
          radius="lg"
          shadow="md"
          isStriped
          classNames={{
            base: "bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden",
            thead: "bg-zinc-800/70 backdrop-blur-sm",
            th: "text-zinc-400 font-medium text-sm py-3 px-4",
            td: "py-3 px-4 text-white/90",
          }}
        >
          <TableHeader>
            <TableColumn>Symbol</TableColumn>
            <TableColumn>Alert Type</TableColumn>
            <TableColumn>Alert Price</TableColumn>
            <TableColumn>Current Price</TableColumn>
            <TableColumn>Difference</TableColumn>
            <TableColumn>Actions</TableColumn>
          </TableHeader>
          <TableBody>{renderTableRows}</TableBody>
        </Table>
      </div>

      {/* Mobile Card Layout */}
      <div className="block mt-4 space-y-4 md:hidden">
        {renderMobileCards}
      </div>

      <Alert
        severity="info"
        sx={{ mt: 4, mb: 3, backgroundColor: alpha(theme.palette.info.main, 0.1) }}
      >
        <Typography variant="body2">
          Price alerts will be triggered automatically when the price conditions
          are met. Click on the chart icon to view the stock chart.
        </Typography>
      </Alert>
    </div>
  );
}
