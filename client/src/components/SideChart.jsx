import React, { useEffect, useRef, useState, useContext } from "react";
import { DataContext } from "../utils/DataContext";
import api from "../utils/api";
import {
  createChart,
  BarSeries,
  ColorType,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";
import { Box, Typography, ToggleButtonGroup, ToggleButton } from "@mui/material";
import { Spinner } from "@nextui-org/react";

function SideChart({ symbol, token }) {
  const { liveData } = useContext(DataContext);
  const [chartData, setChartData] = useState(null);
  const [liveChange, setLiveChange] = useState(null);
  const [OHLC, setOHLC] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const [interval, setInterval] = useState("day");
  const chartContainerRef = useRef();

  // References for chart objects (for real-time updates)
  const chartRef = useRef(null);
  const barSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);

  // References for the three SMA line series
  const ma50SeriesRef = useRef(null);
  const ma150SeriesRef = useRef(null);
  const ma200SeriesRef = useRef(null);

  // Reference to track the last candle we're updating
  const lastCandleRef = useRef(null);

  // --------------------------------------------
  // 1. Helper function to open TradingView chart
  // --------------------------------------------
  const openChart = (symbol) => {
    const timeframe = interval === "week" ? "&timeframe=W" : "";
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}${timeframe}`,
      "_blank"
    );
  };

  // Handle interval change
  const handleIntervalChange = (event, newInterval) => {
    if (newInterval !== null && newInterval !== interval) {
      if (chartRef.current) {
        chartRef.current._isChangingInterval = true;
      }
      setInterval(newInterval);
    }
  };

  // --------------------------------------------
  // 2. Fetch Daily Candle Data
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

      // Transform your data to the structure needed by Lightweight Charts
      const transformedData = response.data.map((item) => ({
        time: item.date.split("T")[0], // e.g. "YYYY-MM-DD"
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

  useEffect(() => {
    if (symbol && token) {
      getChartData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, token, interval]);

  // --------------------------------------------
  // 3. Create Chart and Set Initial Data
  // --------------------------------------------
  useEffect(() => {
    if (!chartData || !chartData.length) return;
    if (!chartContainerRef.current) return;

    if (chartRef.current && !chartRef.current._isChangingInterval) {
      barSeriesRef.current.setData(chartData);
      const volumeData = chartData.map((item) => ({
        time: item.time,
        value: item.volume,
      }));
      volumeSeriesRef.current.setData(volumeData);
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
      lastCandleRef.current = chartData[chartData.length - 1];

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
    
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      barSeriesRef.current = null;
      volumeSeriesRef.current = null;
      ma50SeriesRef.current = null;
      ma150SeriesRef.current = null;
      ma200SeriesRef.current = null;
    }

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

    const seriesData = chartData;

    // Main Bar Series (candlestick-like)
    const barSeries = chart.addSeries(BarSeries, {
      upColor: "#10b981", // emerald-500
      downColor: "#ef4444", // red-500
      borderVisible: false,
      thinBars: false,
    });
    barSeries.setData(seriesData);
    barSeriesRef.current = barSeries;

    // Keep track of the last candle for real-time updates
    lastCandleRef.current = seriesData[seriesData.length - 1];
    setOHLC(seriesData[seriesData.length - 1]);
    setLiveChange(
      ((seriesData[seriesData.length - 1]?.close -
        seriesData[seriesData.length - 2]?.close) /
        seriesData[seriesData.length - 2]?.close) *
        100
    );
    setLivePrice(seriesData[seriesData.length - 1]?.close);

    // Volume Series
    const volumeData = seriesData.map((item) => ({
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

    // SMA lines
    const sma50Data = seriesData.map((item) => ({
      time: item.time,
      value: item.sma_50,
    }));
    const sma150Data = seriesData.map((item) => ({
      time: item.time,
      value: item.sma_150,
    }));
    const sma200Data = seriesData.map((item) => ({
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
    if (seriesData.length > 75) {
      const fromIdx = seriesData.length - 75;
      chart.timeScale().setVisibleRange({
        from: seriesData[fromIdx].time,
        to: seriesData[seriesData.length - 1].time,
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

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [chartData]);

  // --------------------------------------------
  // 4. Real-time Updates (Price, Volume, SMAs)
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
    const tick = liveData.find((t) => t.instrument_token === token);
    if (!tick) return;

    // Extract the new price, volume, SMAs from the real-time feed
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
      volume: interval === 'day' ? newVolume : lastCandleRef.current.volume,
    };

    // If the feed includes updated SMA values, update them too
    if (newSma50 !== undefined) {
      updatedCandle.sma_50 = newSma50;
    }
    if (newSma150 !== undefined) {
      updatedCandle.sma_150 = newSma150;
    }
    if (newSma200 !== undefined) {
      updatedCandle.sma_200 = newSma200;
    }

    // Save the updated candle for future increments
    lastCandleRef.current = updatedCandle;

    // Update the bar/candlestick series (OHLC data)
    barSeriesRef.current.update(updatedCandle);

    // Update volume
    volumeSeriesRef.current.update({
      time: updatedCandle.time,
      value: updatedCandle.volume,
    });
    
    // Update SMA lines if available
    if (newSma50 !== undefined) {
      ma50SeriesRef.current.update({
        time: updatedCandle.time,
        value: newSma50,
      });
    }
    
    if (newSma150 !== undefined) {
      ma150SeriesRef.current.update({
        time: updatedCandle.time,
        value: newSma150,
      });
    }
    
    if (newSma200 !== undefined) {
      ma200SeriesRef.current.update({
        time: updatedCandle.time,
        value: newSma200,
      });
    }
  }, [liveData, chartData, token, interval]);

  // --------------------------------------------
  // 5. UI / Return
  // --------------------------------------------
  if (!symbol || !token) {
    return (
      <Box
        sx={{
          width: "100%",
          height: "100%",
          color: "white",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#18181b", // zinc-900
        }}
      >
        <Typography variant="h6">Select the stock to open the chart</Typography>
      </Box>
    );
  }

  if (!chartData) {
    return (
      <Box
        sx={{
          width: "100%",
          height: "100%",
          color: "white",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#18181b", // zinc-900
        }}
      >
        <Spinner size="lg" />
        <Typography sx={{ mt: 2 }} variant="h6">
          Loading Chart Data
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        height: { xs: "100%", md: "95%" },
        position: "relative",
        backgroundColor: "#18181b", // zinc-900
      }}
    >
      {/* Chart Container */}
      <div ref={chartContainerRef} style={{ width: "100%", height: "100%" }} />

      {/* Stock Info Overlay (top-left corner) */}
      <div
        style={{
          position: "absolute",
          top: "8px",
          left: "8px",
          zIndex: 10,
          backgroundColor: "rgba(39, 39, 42, 0.8)", // zinc-800 with transparency
          color: "#fff",
          padding: "8px 12px",
          borderRadius: "6px",
          border: "1px solid #3f3f46", // zinc-700
          fontSize: "0.9rem",
        }}
        className="flex flex-col justify-center items-left"
      >
        <span className="text-lg font-medium">{symbol}</span>

        <div>
          Change:{" "}
          <span
            className={liveChange > 0 ? "text-emerald-500" : "text-red-500"}
          >
            {liveChange?.toFixed(2)}%
          </span>
        </div>
        <div className="flex flex-wrap gap-2 text-zinc-300">
          <span>
            O: <span className="text-zinc-200">{OHLC?.open?.toFixed(2)}</span>
          </span>
          <span>
            H: <span className="text-zinc-200">{OHLC?.high?.toFixed(2)}</span>
          </span>
          <span>
            L: <span className="text-zinc-200">{OHLC?.low?.toFixed(2)}</span>
          </span>
          <span>
            C: <span className="text-zinc-200">{livePrice?.toFixed(2)}</span>
          </span>
        </div>
      </div>

      {/* Interval Toggle Buttons (top-right corner) */}
      <div
        style={{
          position: "absolute",
          top: "8px",
          right: "8px",
          zIndex: 10,
        }}
      >
        <ToggleButtonGroup
          value={interval}
          exclusive
          onChange={handleIntervalChange}
          size="small"
          sx={{
          backgroundColor: "rgba(39, 39, 42, 0.8)", // zinc-800 with transparency
          border: "1px solid #3f3f46", // zinc-700
            borderRadius: "6px",
            "& .MuiToggleButton-root": {
              color: "#ffffff80",
              fontSize: "0.75rem",
              padding: "4px 8px",
              "&.Mui-selected": {
                backgroundColor: "#3f3f46", // zinc-700
                color: "#ffffff",
              },
            },
          }}
        >
          <ToggleButton value="day">D</ToggleButton>
          <ToggleButton value="week">W</ToggleButton>
        </ToggleButtonGroup>
      </div>
    </Box>
  );
}

export default SideChart;
