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
} from "@mui/material";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
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
import modalStyles from "./ui/ModalStyles";

function ChartModal({
  isOpen,
  onClose,
  symbol,
  token,
  onPrevious,
  onNext,
  hasNext,
  hasPrevious,
  onAddAlert,
}) {
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
      // Error fetching chart data
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
    const timeframe = interval === "week" ? "&timeframe=W" : "";
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}${timeframe}`,
      "_blank"
    );
  };

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      fullWidth
      maxWidth="md"
      PaperProps={{
        sx: {
          ...modalStyles.paper,
          height: "90vh",
          maxHeight: "90vh",
          overflow: "hidden",
        },
      }}
    >
      <DialogTitle sx={modalStyles.title}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Box>
            {symbol}{" "}
            <Typography
              component="span"
              sx={{
                ml: 1,
                px: 1,
                py: 0.3,
                borderRadius: "4px",
                fontSize: "0.7rem",
                fontWeight: "bold",
                backgroundColor: liveChange < 0 ? "#ef4444" : "#10b981",
                color: "white",
              }}
            >
              {liveChange ? liveChange?.toFixed(2) + "%" : "-"}
            </Typography>
          </Box>

          <Box>
            {hasNext || hasPrevious ? (
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <IconButton
                  onClick={onPrevious}
                  disabled={!hasPrevious}
                  size="small"
                  sx={{ color: hasPrevious ? "#a1a1aa" : "#3f3f46" }}
                >
                  <KeyboardArrowUpIcon />
                </IconButton>
                <IconButton
                  onClick={onNext}
                  disabled={!hasNext}
                  size="small"
                  sx={{ color: hasNext ? "#a1a1aa" : "#3f3f46" }}
                >
                  <KeyboardArrowDownIcon />
                </IconButton>
              </Box>
            ) : null}
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent
        sx={{
          ...modalStyles.content,
          p: 1,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            px: 1,
            mb: 1,
          }}
        >
          <ToggleButtonGroup
            value={interval}
            exclusive
            onChange={handleIntervalChange}
            size="small"
            sx={{
              "& .MuiToggleButton-root": {
                color: "#a1a1aa",
                fontSize: "0.75rem",
                px: 1.5,
                py: 0.5,
                borderRadius: "8px",
                borderColor: "rgba(255, 255, 255, 0.1)",
                "&.Mui-selected": {
                  color: "#f4f4f5",
                  backgroundColor: "rgba(99, 102, 241, 0.15)",
                  borderColor: "rgba(99, 102, 241, 0.5)",
                },
              },
            }}
          >
            <ToggleButton value="day">Day</ToggleButton>
            <ToggleButton value="week">Week</ToggleButton>
            <ToggleButton value="month">Month</ToggleButton>
          </ToggleButtonGroup>

          <Box sx={{ display: "flex", alignItems: "center" }}>
            {onAddAlert && (
              <Button
                onClick={() => onAddAlert(symbol, livePrice)}
                size="small"
                sx={{
                  ...modalStyles.primaryButton,
                  mr: 1,
                  fontSize: "0.75rem",
                  py: 0.5,
                  px: 1.5,
                }}
              >
                Add Alert
              </Button>
            )}
            <Button
              onClick={() => openFullChart(symbol)}
              size="small"
              sx={{
                ...modalStyles.secondaryButton,
                fontSize: "0.75rem",
                py: 0.5,
                px: 1.5,
              }}
            >
              Tradingview
            </Button>
          </Box>
        </Box>

        <Box
          sx={{
            display: "flex",
            gap: 1,
            justifyContent: "space-between",
            flexWrap: "wrap",
            mb: 0.5,
            px: 1,
          }}
        >
          {OHLC && (
            <>
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: "#a1a1aa",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <span>O: {OHLC.open?.toFixed(2)}</span>
              </Typography>
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: "#a1a1aa",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <span>H: {OHLC.high?.toFixed(2)}</span>
              </Typography>
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: "#a1a1aa",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <span>L: {OHLC.low?.toFixed(2)}</span>
              </Typography>
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: "#a1a1aa",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <span>C: {OHLC.close?.toFixed(2)}</span>
              </Typography>
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: "#a1a1aa",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <span>LTP: {livePrice?.toFixed(2) || "-"}</span>
              </Typography>
            </>
          )}
        </Box>

        <Box
          ref={chartContainerRef}
          sx={{
            flex: 1,
            width: "100%",
            height: "calc(90vh - 180px)",
            position: "relative",
          }}
        >
          {!chartData && (
            <Box
              sx={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Spinner color="primary" />
            </Box>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={modalStyles.actions}>
        <Button onClick={onClose} sx={modalStyles.secondaryButton}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default ChartModal;
