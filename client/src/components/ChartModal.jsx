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
} from "@mui/material";
import api from "../utils/api";
import {
  createChart,
  BarSeries,
  ColorType,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";
import { DataContext } from "../utils/DataContext";
import { Spinner } from "@nextui-org/react";

function ChartModal({ isOpen, onClose, symbol, token }) {
  const { liveData } = useContext(DataContext);
  const [chartData, setChartData] = useState(null);
  const [liveChange, setLiveChange] = useState(null);
  const [OHLC, setOHLC] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const [interval, setInterval] = useState("day"); // State to track current interval
  const chartContainerRef = useRef(null);

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

  // --------------------------------------------
  // 1. Fetch Chart Data from the backend
  // --------------------------------------------
  const getChartData = async () => {
    if (!symbol || !token) return;
    try {
      setChartData(null);
      setLiveChange(null);
      setOHLC(null);
      setLivePrice(null);
      const response = await api.get(
        `/api/data/chartdata?token=${token}&symbol=${symbol}&interval=${interval}`
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

  // Handle interval change
  const handleIntervalChange = (event, newInterval) => {
    if (newInterval !== null && newInterval !== interval) {
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
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, symbol, token, interval]); // Add interval as dependency

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
      if (chartData.length > 75) {
        const fromIdx = chartData.length - 75;
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
    if (chartData.length > 75) {
      const fromIdx = chartData.length - 75;
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
    // Only apply live updates to daily charts
    if (interval !== "day") return;

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
    const tick = liveData.find((t) => t.instrument_token === token);
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
  }, [liveData, chartData, token]);

  // --------------------------------------------
  // 4. UI / Render Modal
  // --------------------------------------------
  const openFullChart = (symbol) => {
    const timeframe = interval === "week" ? "&timeframe=W" : "";
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}${timeframe}`,
      "_blank"
    );
  };

  return (
    <Dialog
      fullScreen={fullScreen}
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth="xl"
      PaperProps={{
        sx: {
          bgcolor: "#18181b", // zinc-900
          color: "white",
          borderRadius: "12px",
          border: "1px solid #27272a", // zinc-800
          p: 0,
          height: fullScreen ? "100%" : "80vh",
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
        {symbol} {interval === "day" ? "Daily" : "Weekly"} Chart
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

        {/* Interval Toggle Buttons */}
        <div className="absolute top-3 right-3 z-10">
          <div className="bg-zinc-900/80 backdrop-blur-md border border-zinc-800 rounded-lg overflow-hidden shadow-lg">
            <div className="flex">
              <button
                className={`px-3 py-1.5 text-xs font-medium ${
                  interval === "day"
                    ? "bg-zinc-700 text-white"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
                }`}
                onClick={() => handleIntervalChange(null, "day")}
              >
                Daily
              </button>
              <button
                className={`px-3 py-1.5 text-xs font-medium ${
                  interval === "week"
                    ? "bg-zinc-700 text-white"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
                }`}
                onClick={() => handleIntervalChange(null, "week")}
              >
                Weekly
              </button>
            </div>
          </div>
        </div>

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
            fontSize: "0.875rem",
            py: 0.75,
            px: 2,
            "&:hover": {
              borderColor: "#52525b", // zinc-600
              bgcolor: "rgba(82, 82, 91, 0.1)",
            },
          }}
        >
          Open in TradingView
        </Button>
        <Button
          onClick={getChartData}
          variant="outlined"
          sx={{
            color: "#10b981", // emerald-500
            borderColor: "#064e3b", // emerald-900
            borderRadius: "8px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: "0.875rem",
            py: 0.75,
            px: 2,
            "&:hover": {
              borderColor: "#047857", // emerald-700
              bgcolor: "rgba(16, 185, 129, 0.1)",
            },
          }}
        >
          Refresh
        </Button>
        <Button
          onClick={onClose}
          variant="outlined"
          sx={{
            ml: "auto",
            color: "#ef4444", // red-500
            borderColor: "#7f1d1d", // red-900
            borderRadius: "8px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: "0.875rem",
            py: 0.75,
            px: 2,
            "&:hover": {
              borderColor: "#b91c1c", // red-700
              bgcolor: "rgba(239, 68, 68, 0.1)",
            },
          }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default ChartModal;
