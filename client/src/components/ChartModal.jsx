import React, { useEffect, useRef, useState, useContext } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  useTheme,
  useMediaQuery,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
  Tab,
  Tabs,
  Chip,
  Divider,
} from "@mui/material";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import DeleteIcon from "@mui/icons-material/Delete";
import CloseIcon from "@mui/icons-material/Close";
import api from "../utils/api";
import {
  createChart,
  BarSeries,
  ColorType,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";
import { DataContext } from "../utils/DataContext";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode";
import { Spinner } from "@nextui-org/react";
import { toast } from "sonner";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";
import ModifySlModal from "./ModifySlModal";
import ModifyTgtModal from "./ModifyTgtModal";
import IncreaseModal from "./IncreaseModal";
import ReduceModal from "./ReduceModal";
import RiskMeter from "./RiskMeter";
import { getSimpleRiskScore } from "../utils/api.js";

function ChartModal({
  isOpen,
  onClose,
  symbol,
  token: instrumentToken,
  onPrevious,
  onNext,
  hasNext,
  hasPrevious,
  onAddAlert,
  onBuy,
}) {
  const { liveData, priceAlerts, positions } = useContext(DataContext);
  const { token } = useContext(AuthContext);
  const [chartData, setChartData] = useState(null);
  const [liveChange, setLiveChange] = useState(null);
  const [OHLC, setOHLC] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const [interval, setInterval] = useState("day"); // State to track current interval
  const chartContainerRef = useRef(null);
  
  // State for the side panel tabs
  const [tabValue, setTabValue] = useState(0);
  const [isDeleteLoading, setIsDeleteLoading] = useState(false);
  const [isPanelVisible, setIsPanelVisible] = useState(false);

  // Refs for chart objects and series
  const chartRef = useRef(null);
  const barSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const ma50SeriesRef = useRef(null);
  const ma150SeriesRef = useRef(null);
  const ma200SeriesRef = useRef(null);
  // Reference to track the last candle
  const lastCandleRef = useRef(null);

  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));
  const isSm = useMediaQuery(theme.breakpoints.down("sm"));

  // Filter alerts and positions for the current symbol
  const symbolAlerts = priceAlerts?.filter(alert => alert.symbol === symbol) || [];
  const symbolPosition = positions?.find(pos => pos.stock_name === symbol);
  
  // State for modals
  const [isModifySlModalOpen, setIsModifySlModalOpen] = useState(false);
  const [isModifyTgtModalOpen, setIsModifyTgtModalOpen] = useState(false);
  const [isIncreaseModalOpen, setIsIncreaseModalOpen] = useState(false);
  const [isReduceModalOpen, setIsReduceModalOpen] = useState(false);
  const [isExitLoading, setIsExitLoading] = useState(false);

  // Risk score state
  const [riskScore, setRiskScore] = useState(null);
  const [isLoadingRisk, setIsLoadingRisk] = useState(false);

  // Add multiplier logic
  let multiplier = 1;
  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token);
      userRole = decoded.role || "";
      if (userRole !== "admin") {
        multiplier = 25;
      }
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // Calculate live P&L for the position if it exists
  const calculateLivePnL = () => {
    if (!symbolPosition || !livePrice) return { pnl: 0, pnlPercent: 0 };
    
    const entryPrice = symbolPosition.entry_price;
    const qty = symbolPosition.current_qty;
    const pnl = (livePrice - entryPrice) * qty;
    const pnlPercent = ((livePrice - entryPrice) / entryPrice) * 100;
    
    return { pnl, pnlPercent };
  };
  
  // Calculate SL and Target percentages
  const calculateRiskReward = () => {
    if (!symbolPosition || !symbolPosition.entry_price) return { slPercent: null, targetPercent: null };
    
    const entryPrice = symbolPosition.entry_price;
    let slPercent = null;
    let targetPercent = null;
    
    if (symbolPosition.stop_loss) {
      slPercent = Math.abs(((symbolPosition.stop_loss - entryPrice) / entryPrice) * 100);
    }
    
    if (symbolPosition.target) {
      targetPercent = Math.abs(((symbolPosition.target - entryPrice) / entryPrice) * 100);
    }
    
    return { slPercent, targetPercent };
  };
  
  const livePnL = calculateLivePnL();
  const riskReward = calculateRiskReward();
  
  // Function to toggle panel visibility
  const togglePanel = () => {
    setIsPanelVisible(!isPanelVisible);
  };

  // --------------------------------------------
  // 1. Fetch Chart Data from the backend
  // --------------------------------------------
  const getChartData = async () => {
    if (!symbol || !instrumentToken) return;
    try {
      setChartData(null);
      setLiveChange(null);
      setOHLC(null);
      setLivePrice(null);
      const response = await api.get(
        `/api/data/chartdata?token=${instrumentToken}&symbol=${symbol}&interval=${interval}`
      );
      const transformedData = response.data.map((item) => ({
        time: item.date.split("T")[0],
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
        volume: item.volume,
        ...(item.sma_50 !== 0 ? { sma_50: item.sma_50 } : {}),
        ...(item.sma_150 !== 0 ? { sma_150: item.sma_150 } : {}),
        ...(item.sma_200 !== 0 ? { sma_200: item.sma_200 } : {}),
      }));
      setChartData(transformedData);
    } catch (error) {
      console.error("Error fetching chart data:", error);
    }
  };

  // --------------------------------------------
  // Fetch Risk Score for the symbol
  // --------------------------------------------
  const getRiskScore = async () => {
    if (!symbol) return;
    try {
      setIsLoadingRisk(true);
      const response = await getSimpleRiskScore(symbol);
      setRiskScore(response);
    } catch (error) {
      console.error("Error fetching risk score:", error);
      setRiskScore(null);
    } finally {
      setIsLoadingRisk(false);
    }
  };

  // Handle interval change
  const handleIntervalChange = (event, newInterval) => {
    // Only allow "day" interval since weekly charts are removed
    if (newInterval === "day" && newInterval !== interval) {
      // Mark that we're changing intervals so the chart will be recreated
      if (chartRef.current) {
        chartRef.current._isChangingInterval = true;
      }
      setInterval(newInterval);
    }
  };

  useEffect(() => {
    if (isOpen) {
      getChartData();
      getRiskScore();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, symbol, instrumentToken, interval]); // Add interval as dependency

  // --------------------------------------------
  // 2. Create the chart (or update series if already created)
  // --------------------------------------------
  useEffect(() => {
    if (!chartData || !chartData.length) return;
    if (!chartContainerRef.current) return;

    // If the chart already exists and we're not changing intervals, just update the series data
    if (chartRef.current && !chartRef.current._isChangingInterval) {
      // Update main (bar) series
      barSeriesRef.current.setData(chartData);
      // Update volume series
      const volumeData = chartData.map((item) => ({
        time: item.time,
        value: item.volume,
      }));
      volumeSeriesRef.current.setData(volumeData);
      // Update SMA line series
      const sma50Data = chartData.map((item) => ({
        time: item.time,
        value: item.sma_50,
      }));
      const sma150Data = chartData.map((item) => ({
        time: item.time,
        value: item.sma_150,
      }));
      const sma200Data = chartData.map((item) => ({
        time: item.time,
        value: item.sma_200,
      }));
      ma50SeriesRef.current.setData(sma50Data);
      ma150SeriesRef.current.setData(sma150Data);
      ma200SeriesRef.current.setData(sma200Data);
      // Update our reference to the last candle
      lastCandleRef.current = chartData[chartData.length - 1];

      // Adjust visible range when updating data
      if (chartData.length > 150) {
        const fromIdx = chartData.length - 150;
        chartRef.current.timeScale().setVisibleRange({
          from: chartData[fromIdx].time,
          to: chartData[chartData.length - 1].time,
        });
      } else {
        chartRef.current.timeScale().fitContent();
      }

      return;
    }

    // When interval changes or initializing, remove the old chart if it exists
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      barSeriesRef.current = null;
      volumeSeriesRef.current = null;
      ma50SeriesRef.current = null;
      ma150SeriesRef.current = null;
      ma200SeriesRef.current = null;
    }

    // Otherwise, create the chart for the first time
    const container = chartContainerRef.current;
    const getDimensions = () => ({
      width: container.clientWidth,
      height: container.clientHeight,
    });
    const { width, height } = getDimensions();

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "#18181b" }, // zinc-900
        textColor: "#e4e4e7", // zinc-200
      },
      width,
      height,
      grid: {
        vertLines: { color: "#27272a" }, // zinc-800
        horzLines: { color: "#27272a" }, // zinc-800
      },
      crosshair: { mode: 0 },
    });
    chartRef.current = chart;

    // Main bar series (candlestick-like)
    const barSeries = chart.addSeries(BarSeries, {
      upColor: "#10b981", // emerald-500
      downColor: "#ef4444", // red-500
      borderVisible: false,
      thinBars: false,
    });
    barSeries.setData(chartData);
    barSeriesRef.current = barSeries;
    // Save the last candle for live updates
    lastCandleRef.current = chartData[chartData.length - 1];

    setOHLC(chartData[chartData.length - 1]);
    setLiveChange(
      ((chartData[chartData.length - 1]?.close -
        chartData[chartData.length - 2]?.close) /
        chartData[chartData.length - 2]?.close) *
        100
    );
    setLivePrice(chartData[chartData.length - 1]?.close);

    // Volume histogram series
    const volumeData = chartData.map((item) => ({
      time: item.time,
      value: item.volume,
    }));
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#a1a1aa80", // zinc-400 with transparency
      priceFormat: { type: "volume" },
      priceScaleId: "",
      scaleMargins: { top: 0.9, bottom: 0 },
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.9, bottom: 0 },
    });
    volumeSeries.setData(volumeData);
    volumeSeriesRef.current = volumeSeries;

    // SMA line series
    const sma50Data = chartData.map((item) => ({
      time: item.time,
      value: item.sma_50,
    }));
    const sma150Data = chartData.map((item) => ({
      time: item.time,
      value: item.sma_150,
    }));
    const sma200Data = chartData.map((item) => ({
      time: item.time,
      value: item.sma_200,
    }));

    const ma50Series = chart.addSeries(LineSeries, {
      color: "#3b82f680", // blue-500 with transparency
      lineWidth: 2,
    });
    ma50Series.setData(sma50Data);
    ma50SeriesRef.current = ma50Series;

    const ma150Series = chart.addSeries(LineSeries, {
      color: "#10b98180", // emerald-500 with transparency
      lineWidth: 2,
    });
    ma150Series.setData(sma150Data);
    ma150SeriesRef.current = ma150Series;

    const ma200Series = chart.addSeries(LineSeries, {
      color: "#f59e0b80", // amber-500 with transparency
      lineWidth: 2,
    });
    ma200Series.setData(sma200Data);
    ma200SeriesRef.current = ma200Series;

    // Adjust visible range
    if (chartData.length > 150) {
      const fromIdx = chartData.length - 150;
      chart.timeScale().setVisibleRange({
        from: chartData[fromIdx].time,
        to: chartData[chartData.length - 1].time,
      });
    } else {
      chart.timeScale().fitContent();
    }

    // Resize handler
    const handleResize = () => {
      const { width, height } = getDimensions();
      chart.applyOptions({ width, height });
    };
    window.addEventListener("resize", handleResize);

    // Cleanup on unmount
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [chartData]);

  // --------------------------------------------
  // 3. Real-Time Updates via .update() on the last candle
  // --------------------------------------------
  useEffect(() => {
    if (
      !liveData ||
      !liveData.length ||
      !chartData ||
      !chartData.length ||
      !barSeriesRef.current ||
      !volumeSeriesRef.current ||
      !ma50SeriesRef.current ||
      !ma150SeriesRef.current ||
      !ma200SeriesRef.current ||
      !lastCandleRef.current
    ) {
      return;
    }

    // Find the tick for this token
    const tick = liveData.find((t) => t.instrument_token === instrumentToken);
    if (!tick) return;

    // Extract the new values from the real-time feed
    const newPrice = tick.last_price;
    const newVolume = tick.volume_traded;
    const newSma50 = tick.sma_50;
    const newSma150 = tick.sma_150;
    const newSma200 = tick.sma_200;

    setLiveChange(tick.change);
    setOHLC(tick.ohlc);
    setLivePrice(newPrice);

    // Update the last candle
    const updatedCandle = {
      ...lastCandleRef.current,
      close: newPrice,
      high: Math.max(lastCandleRef.current.high, newPrice),
      low: Math.min(lastCandleRef.current.low, newPrice),
      volume: newVolume,
    };
    if (newSma50 !== undefined) {
      updatedCandle.sma_50 = newSma50;
    }
    if (newSma150 !== undefined) {
      updatedCandle.sma_150 = newSma150;
    }
    if (newSma200 !== undefined) {
      updatedCandle.sma_200 = newSma200;
    }

    // Save the updated candle and update the chart using .update()
    lastCandleRef.current = updatedCandle;
    barSeriesRef.current.update(updatedCandle);
    volumeSeriesRef.current.update({
      time: updatedCandle.time,
      value: updatedCandle.volume,
    });
  }, [liveData, chartData, instrumentToken]);

  // Listen for keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      if (e.key === "ArrowUp" && hasPrevious) {
        onPrevious();
      } else if (e.key === "ArrowDown" && hasNext) {
        onNext();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onNext, onPrevious, hasNext, hasPrevious]);

  // --------------------------------------------
  // 4. UI / Render Modal
  // --------------------------------------------
  const openFullChart = (symbol) => {
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}`,
      "_blank"
    );
  };

  // New function for handling tab changes
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Function to delete an alert
  const handleDeleteAlert = async (alertId) => {
    setIsDeleteLoading(true);
    try {
      await api.delete("/api/alerts/remove", { params: { alert_id: alertId } });
      toast.success("Alert removed successfully", {
        duration: 5000,
      });
    } catch (error) {
      toast.error("Failed to delete alert", {
        duration: 5000,
      });
    } finally {
      setIsDeleteLoading(false);
    }
  };

  // Functions to handle position actions
  const handleExitPosition = async () => {
    setIsExitLoading(true);
    try {
      const response = await api.get(`/api/order/exit?symbol=${symbol}`);
      PlayToastSound();
      toast.success(
        response?.data?.message || "Position exited successfully!",
        { duration: 5000 }
      );
    } catch (error) {
      PlayErrorSound();
      toast.error("Error exiting position.", { duration: 5000 });
    } finally {
      setIsExitLoading(false);
    }
  };

  const calculateDifference = (alertPrice) => {
    if (!livePrice) return null;
    const difference = ((livePrice - alertPrice) / alertPrice) * 100;
    return difference.toFixed(2);
  };

  // Modal handlers
  const handleOpenModifySlModal = () => setIsModifySlModalOpen(true);
  const handleCloseModifySlModal = () => setIsModifySlModalOpen(false);

  const handleOpenModifyTgtModal = () => setIsModifyTgtModalOpen(true);
  const handleCloseModifyTgtModal = () => setIsModifyTgtModalOpen(false);
  
  const handleOpenIncreaseModal = () => setIsIncreaseModalOpen(true);
  const handleCloseIncreaseModal = () => setIsIncreaseModalOpen(false);
  
  const handleOpenReduceModal = () => setIsReduceModalOpen(true);
  const handleCloseReduceModal = () => setIsReduceModalOpen(false);

  return (
    <Dialog
      fullScreen={fullScreen}
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth="2xl"
      PaperProps={{
        sx: {
          bgcolor: "#18181b", // zinc-900
          color: "white",
          borderRadius: "12px",
          border: "1px solid #27272a", // zinc-800
          p: 0,
          height: fullScreen ? "100%" : "90vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          color: "white",
          fontSize: "1.2rem",
          px: 3,
          py: 2,
          bgcolor: "#18181b", // zinc-900
          borderBottom: "1px solid #27272a", // zinc-800
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-lg font-bold text-zinc-200 mr-2">
              {symbol}
            </span>
            {liveChange !== null && (
              <span
                className={`text-sm font-medium ${
                  liveChange >= 0 ? "text-green-500" : "text-red-500"
                }`}
              >
                {liveChange >= 0 ? "+" : ""}
                {liveChange?.toFixed(2)}%
              </span>
            )}
          </div>
          <div className="flex items-center space-x-1">
            <IconButton
              size="small"
              disabled={!hasPrevious}
              onClick={onPrevious}
              sx={{
                color: hasPrevious ? "white" : "gray",
                "&:hover": {
                  backgroundColor: hasPrevious
                    ? "rgba(255, 255, 255, 0.1)"
                    : "transparent",
                },
              }}
            >
              <KeyboardArrowUpIcon />
            </IconButton>
            <IconButton
              size="small"
              disabled={!hasNext}
              onClick={onNext}
              sx={{
                color: hasNext ? "white" : "gray",
                "&:hover": {
                  backgroundColor: hasNext
                    ? "rgba(255, 255, 255, 0.1)"
                    : "transparent",
                },
              }}
            >
              <KeyboardArrowDownIcon />
            </IconButton>
          </div>
        </div>
      </DialogTitle>
      <DialogContent
        sx={{
          p: 0,
          height: fullScreen ? "calc(100% - 130px)" : "calc(80vh - 130px)",
          overflow: "hidden",
          bgcolor: "#18181b", // zinc-900
          position: "relative",
        }}
      >
        {!chartData && (
          <Box sx={{ p: 0, height: "100%" }}>
            <div className="flex flex-col items-center justify-center w-full h-full">
              <Spinner size="lg" />
              <span className="m-5 text-xl font-medium text-zinc-300">
                Loading Chart Data
              </span>
            </div>
          </Box>
        )}
        <div className="absolute top-3 left-3 z-10 bg-zinc-900/80 backdrop-blur-md text-white px-3 py-2 rounded-lg border border-zinc-800 shadow-lg">
          <div className="text-sm font-medium mb-1">{symbol}</div>
          <div className="text-xs mb-1">
            Change:{" "}
            <span
              className={
                liveChange > 0
                  ? "text-emerald-500 font-medium"
                  : "text-red-500 font-medium"
              }
            >
              {liveChange?.toFixed(2)}%
            </span>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-zinc-300">
            <span>
              O: <span className="text-white">{OHLC?.open?.toFixed(2)}</span>
            </span>
            <span>
              H: <span className="text-white">{OHLC?.high?.toFixed(2)}</span>
            </span>
            <span>
              L: <span className="text-white">{OHLC?.low?.toFixed(2)}</span>
            </span>
            <span>
              C: <span className="text-white">{livePrice?.toFixed(2)}</span>
            </span>
          </div>
        </div>

        {/* Risk Meter - Top Right */}
        <div className="absolute top-3 right-20 z-10 bg-zinc-900/80 backdrop-blur-md text-white px-3 py-2 rounded-lg border border-zinc-800 shadow-lg">
          <div className="text-xs font-medium mb-2 text-zinc-300">Risk Score</div>
          {isLoadingRisk ? (
            <div className="flex items-center justify-center h-6">
              <div className="animate-spin w-4 h-4 border-2 border-zinc-600 border-t-white rounded-full"></div>
            </div>
          ) : riskScore?.overall_risk_score !== null && riskScore?.overall_risk_score !== undefined ? (
            <RiskMeter 
              riskScore={riskScore.overall_risk_score} 
              size="sm" 
              showLabel={true}
              className="justify-center"
            />
          ) : (
            <div className="flex items-center justify-center h-6">
              <span className="text-xs text-zinc-500">Not Available</span>
            </div>
          )}
          
        </div>

        {/* Side panel for alerts and positions */}
        {isPanelVisible && (
          <div className="absolute bottom-4 left-4 z-10 bg-zinc-900/90 backdrop-blur-md text-white rounded-lg border border-zinc-800 shadow-lg max-w-[300px] w-full">
            <div className="flex justify-between items-center px-2 py-1 border-b border-zinc-800">
              <Tabs 
                value={tabValue} 
                onChange={handleTabChange} 
                variant="fullWidth"
                sx={{ 
                  '& .MuiTab-root': {
                    color: '#a1a1aa',
                    fontSize: '0.75rem', 
                    minHeight: '36px',
                    '&.Mui-selected': {
                      color: '#e4e4e7',
                    }
                  },
                  '& .MuiTabs-indicator': {
                    backgroundColor: '#3b82f6',
                  }
                }}
              >
                <Tab label="Alerts" />
                <Tab label="Position" disabled={!symbolPosition} />
              </Tabs>
              <IconButton
                size="small"
                onClick={togglePanel}
                sx={{ 
                  color: '#a1a1aa',
                  p: 0.5,
                  '&:hover': {
                    color: '#e4e4e7',
                  }
                }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </div>
            
            <Box sx={{ p: 2, maxHeight: '250px', overflowY: 'auto' }}>
              {tabValue === 0 && (
                <>
                  {symbolAlerts.length > 0 ? (
                    <>
                      {symbolAlerts.map(alert => (
                        <Box key={alert.id} sx={{ mb: 2, pb: 2, borderBottom: '1px solid #27272a' }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                            <Chip
                              label={alert.alert_type === "sl" ? "Stop Loss" : "Target"}
                              size="small"
                              sx={{
                                bgcolor: alert.alert_type === "sl" ? "#ef4444" : "#22c55e",
                                color: "white",
                                fontSize: '0.65rem',
                                height: '20px'
                              }}
                            />
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteAlert(alert.id)}
                              disabled={isDeleteLoading}
                              sx={{ p: 0.5 }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span className="text-zinc-400">Alert Price:</span>
                            <span className="font-medium">₹{alert.price.toFixed(2)}</span>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span className="text-zinc-400">Current:</span>
                            <span className="font-medium">₹{livePrice?.toFixed(2) || "--"}</span>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                            <span className="text-zinc-400">Difference:</span>
                            <span className={`font-medium ${parseFloat(calculateDifference(alert.price)) >= 0 ? "text-green-500" : "text-red-500"}`}>
                              {calculateDifference(alert.price)}%
                            </span>
                          </Box>
                        </Box>
                      ))}
                    </>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 2 }}>
                      <Typography variant="body2" sx={{ color: '#a1a1aa', fontSize: '0.85rem' }}>
                        No alerts set for this stock
                      </Typography>
                      <Button
                        onClick={() => onAddAlert(symbol, instrumentToken, livePrice)}
                        variant="outlined"
                        size="small"
                        sx={{
                          mt: 1,
                          color: "#3b82f6",
                          borderColor: "#1e3a8a",
                          fontSize: "0.75rem",
                          py: 0.5,
                          textTransform: "none",
                          "&:hover": {
                            borderColor: "#1d4ed8",
                            bgcolor: "rgba(59, 130, 246, 0.1)",
                          },
                        }}
                      >
                        Add Alert
                      </Button>
                    </Box>
                  )}
                </>
              )}
              
              {tabValue === 1 && symbolPosition && (
                <Box sx={{ fontSize: '0.8rem' }}>
                  <Box sx={{ mb: 2 }}>
                    <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem', mb: 1 }}>OVERVIEW</Typography>
                    <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                      <Box>
                        <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem' }}>Entry Price</Typography>
                        <Typography sx={{ fontSize: '0.85rem', fontWeight: 500 }}>
                          ₹{symbolPosition.entry_price.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem' }}>Quantity</Typography>
                        <Typography sx={{ fontSize: '0.85rem', fontWeight: 500 }}>
                          {symbolPosition.current_qty * multiplier}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem' }}>Capital Used</Typography>
                        <Typography sx={{ fontSize: '0.85rem', fontWeight: 500 }}>
                          ₹{(symbolPosition.entry_price * symbolPosition.current_qty * multiplier).toFixed(2)}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem' }}>Live P&L</Typography>
                        <Typography sx={{ 
                          fontSize: '0.85rem', 
                          fontWeight: 500,
                          color: livePnL.pnl >= 0 ? '#22c55e' : '#ef4444'
                        }}>
                          ₹{(livePnL.pnl * multiplier).toFixed(2)}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem' }}>P&L %</Typography>
                        <Typography sx={{ 
                          fontSize: '0.85rem', 
                          fontWeight: 500,
                          color: livePnL.pnlPercent >= 0 ? '#22c55e' : '#ef4444'
                        }}>
                          {livePnL.pnlPercent.toFixed(2)}%
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                  
                  <Box sx={{ mb: 2 }}>
                    <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem', mb: 1 }}>RISK MANAGEMENT</Typography>
                    <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                      <Box>
                        <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem' }}>Stop Loss</Typography>
                        <Typography sx={{ fontSize: '0.85rem', fontWeight: 500 }}>
                          {symbolPosition.stop_loss ? (
                            <>
                              ₹{symbolPosition.stop_loss.toFixed(2)}
                              <span className="ml-1 text-xs text-zinc-400">
                                ({riskReward.slPercent?.toFixed(1)}%)
                              </span>
                            </>
                          ) : (
                            'Not Set'
                          )}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography sx={{ color: '#a1a1aa', fontSize: '0.7rem' }}>Target</Typography>
                        <Typography sx={{ fontSize: '0.85rem', fontWeight: 500 }}>
                          {symbolPosition.target ? (
                            <>
                              ₹{symbolPosition.target.toFixed(2)}
                              <span className="ml-1 text-xs text-zinc-400">
                                ({riskReward.targetPercent?.toFixed(1)}%)
                              </span>
                            </>
                          ) : (
                            'Not Set'
                          )}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                  
                  <Divider sx={{ borderColor: '#27272a', my: 1.5 }} />
                  
                  {userRole === "admin" && (
                    <>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <Button
                          variant="outlined"
                          size="small"
                          sx={{
                            color: "#ef4444",
                            borderColor: "#7f1d1d",
                            fontSize: "0.7rem",
                            py: 0.5,
                            minWidth: 0,
                            flex: "1 0 auto",
                            textTransform: "none",
                            "&:hover": {
                              borderColor: "#b91c1c",
                              bgcolor: "rgba(239, 68, 68, 0.1)",
                            },
                          }}
                          onClick={handleExitPosition}
                          disabled={isExitLoading}
                        >
                          Exit
                        </Button>
                        <Button
                          variant="outlined"
                          size="small"
                          sx={{
                            color: "#10b981",
                            borderColor: "#064e3b",
                            fontSize: "0.7rem",
                            py: 0.5,
                            minWidth: 0,
                            flex: "1 0 auto",
                            textTransform: "none",
                            "&:hover": {
                              borderColor: "#047857",
                              bgcolor: "rgba(16, 185, 129, 0.1)",
                            },
                          }}
                          onClick={handleOpenIncreaseModal}
                        >
                          Add
                        </Button>
                        <Button
                          variant="outlined"
                          size="small"
                          sx={{
                            color: "#f59e0b",
                            borderColor: "#78350f",
                            fontSize: "0.7rem",
                            py: 0.5,
                            minWidth: 0,
                            flex: "1 0 auto",
                            textTransform: "none",
                            "&:hover": {
                              borderColor: "#92400e",
                              bgcolor: "rgba(245, 158, 11, 0.1)",
                            },
                          }}
                          onClick={handleOpenReduceModal}
                        >
                          Reduce
                        </Button>
                      </Box>
                      
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                        <Button
                          variant="outlined"
                          size="small"
                          sx={{
                            color: "#3b82f6",
                            borderColor: "#1e3a8a",
                            fontSize: "0.7rem",
                            py: 0.5,
                            minWidth: 0,
                            flex: "1 0 auto",
                            textTransform: "none",
                            "&:hover": {
                              borderColor: "#1d4ed8",
                              bgcolor: "rgba(59, 130, 246, 0.1)",
                            },
                          }}
                          onClick={handleOpenModifySlModal}
                        >
                          Modify SL
                        </Button>
                        <Button
                          variant="outlined"
                          size="small"
                          sx={{
                            color: "#8b5cf6",
                            borderColor: "#4c1d95",
                            fontSize: "0.7rem",
                            py: 0.5,
                            minWidth: 0,
                            flex: "1 0 auto",
                            textTransform: "none",
                            "&:hover": {
                              borderColor: "#6d28d9",
                              bgcolor: "rgba(139, 92, 246, 0.1)",
                            },
                          }}
                          onClick={handleOpenModifyTgtModal}
                        >
                          Modify Target
                        </Button>
                      </Box>
                    </>
                  )}
                </Box>
              )}
            </Box>
          </div>
        )}
        
        {/* Button to show the panel if hidden */}
        {!isPanelVisible && (
          <Button
            onClick={togglePanel}
            variant="contained"
            size="small"
            sx={{
              position: 'absolute',
              bottom: '4px',
              left: '4px',
              zIndex: 10,
              minWidth: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: '#3b82f6',
              color: 'white',
              '&:hover': {
                backgroundColor: '#2563eb',
              },
              p: 0.5
            }}
          >
            <span className="font-medium text-xs">Info</span>
          </Button>
        )}

        

        <div
          ref={chartContainerRef}
          style={{ width: "100%", height: "100%" }}
        />
      </DialogContent>
      <DialogActions
        sx={{
          p: 2,
          bgcolor: "#18181b", // zinc-900
          borderTop: "1px solid #27272a", // zinc-800
          gap: 1,
          flexWrap: "wrap", // Allow buttons to wrap on smaller screens
          justifyContent: "flex-end", // Keep buttons right-aligned
        }}
      >
        <Button
          onClick={() => openFullChart(symbol)}
          variant="outlined"
          sx={{
            color: "#e4e4e7", // zinc-200
            borderColor: "#3f3f46", // zinc-700
            borderRadius: "8px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: { xs: "0.75rem", sm: "0.875rem" },
            py: 0.75,
            px: { xs: 1.5, sm: 2 },
            mb: { xs: 1, sm: 0 },
            "&:hover": {
              borderColor: "#52525b", // zinc-600
              bgcolor: "rgba(82, 82, 91, 0.1)",
            },
          }}
        >
          <span className="hidden sm:inline">Open in TradingView</span>
          <span className="sm:hidden">TWC</span>
        </Button>
        {/* Only show Buy button if we have the onBuy prop AND no existing position */}
        {onBuy && !symbolPosition && (
          <Button
            onClick={() => onBuy(symbol, instrumentToken, livePrice)}
            variant="outlined"
            sx={{
              color: "#22c55e", // green-500
              borderColor: "#14532d", // green-900
              borderRadius: "8px",
              textTransform: "none",
              fontWeight: "normal",
              fontSize: { xs: "0.75rem", sm: "0.875rem" },
              py: 0.75,
              px: { xs: 1.5, sm: 2 },
              mb: { xs: 1, sm: 0 },
              "&:hover": {
                borderColor: "#15803d", // green-700
                bgcolor: "rgba(34, 197, 94, 0.1)",
              },
            }}
          >
            Buy
          </Button>
        )}
        <Button
          onClick={() => onAddAlert(symbol, instrumentToken, livePrice)}
          variant="outlined"
          sx={{
            color: "#3b82f6", // blue-500
            borderColor: "#1e3a8a", // blue-900
            borderRadius: "8px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: { xs: "0.75rem", sm: "0.875rem" },
            py: 0.75,
            px: { xs: 1.5, sm: 2 },
            mb: { xs: 1, sm: 0 },
            "&:hover": {
              borderColor: "#1d4ed8", // blue-700
              bgcolor: "rgba(59, 130, 246, 0.1)",
            },
          }}
        >
          <span className="hidden sm:inline">Add Alert</span>
          <span className="sm:hidden">Alert</span>
        </Button>
        <Button
          onClick={onClose}
          variant="outlined"
          sx={{
            ml: { xs: 0, sm: "auto" },
            color: "#ef4444", // red-500
            borderColor: "#7f1d1d", // red-900
            borderRadius: "8px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: { xs: "0.75rem", sm: "0.875rem" },
            py: 0.75,
            px: { xs: 1.5, sm: 2 },
            "&:hover": {
              borderColor: "#b91c1c", // red-700
              bgcolor: "rgba(239, 68, 68, 0.1)",
            },
          }}
        >
          Close
        </Button>
      </DialogActions>
      
      {/* Modal components for position management */}
      {symbolPosition && userRole === "admin" && (
        <>
          <ModifySlModal
            isOpen={isModifySlModalOpen}
            onClose={handleCloseModifySlModal}
            symbol={symbol}
            currentEntryPrice={symbolPosition.entry_price}
            currentSl={symbolPosition.stop_loss}
          />
          
          <ModifyTgtModal
            isOpen={isModifyTgtModalOpen}
            onClose={handleCloseModifyTgtModal}
            symbol={symbol}
            currentEntryPrice={symbolPosition.entry_price}
            currentTarget={symbolPosition.target}
          />
          
          <IncreaseModal
            isOpen={isIncreaseModalOpen}
            onClose={handleCloseIncreaseModal}
            symbol={symbol}
            token={instrumentToken}
            entry={symbolPosition.entry_price}
            ltp={livePrice || symbolPosition.last_price}
            qty={symbolPosition.current_qty}
          />
          
          <ReduceModal
            isOpen={isReduceModalOpen}
            onClose={handleCloseReduceModal}
            symbol={symbol}
            currentQty={symbolPosition.current_qty}
          />
        </>
      )}
    </Dialog>
  );
}

export default ChartModal;
