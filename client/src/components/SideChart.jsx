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
import { Box, Typography } from "@mui/material";
import { Spinner } from "@nextui-org/react";

function SideChart({ symbol, token }) {
  const { liveData } = useContext(DataContext);
  const [chartData, setChartData] = useState(null);
  const [liveChange, setLiveChange] = useState(null);
  const [OHLC, setOHLC] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const chartContainerRef = useRef();

  // References for chart objects (for real-time updates)
  const chartRef = useRef(null);
  const barSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);

  // References for the three SMA line series
  const ma50SeriesRef = useRef(null);
  const ma100SeriesRef = useRef(null);
  const ma200SeriesRef = useRef(null);

  // Reference to track the last candle we're updating
  const lastCandleRef = useRef(null);

  // --------------------------------------------
  // 1. Helper function to open TradingView chart
  // --------------------------------------------
  const openChart = (symbol) => {
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}`,
      "_blank"
    );
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
      const encodedSymbol = encodeURIComponent(symbol).replace(/&/g, '%26');
      const response = await api.get(
        `/api/data/chartdata?token=${token}&symbol=${encodedSymbol}`
      );

      // Process and sort data to ensure proper time ordering
      const processedData = response.data.map((item) => ({
        time: item.date.split("T")[0], // Extract date part for daily charts
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
        volume: item.volume,
        // Include SMA values only if they are valid (greater than 0)
        sma_50: item.sma_50 != null && item.sma_50 > 0 ? item.sma_50 : null,
        sma_100: item.sma_100 != null && item.sma_100 > 0 ? item.sma_100 : null,
        sma_200: item.sma_200 != null && item.sma_200 > 0 ? item.sma_200 : null,
        originalDate: item.date, // Keep original for sorting
        // Add a unique key for better duplicate detection
        originalTimestamp: new Date(item.date).getTime(),
      }));

      // Sort by original datetime to maintain proper order
      processedData.sort((a, b) => new Date(a.originalDate) - new Date(b.originalDate));

      // Improved duplicate removal - keep the most recent entry for each date
      // Group by date and keep only the latest entry (highest timestamp)
      const dateGroups = {};
      processedData.forEach(item => {
        const dateKey = item.time;
        if (!dateGroups[dateKey] || item.originalTimestamp > dateGroups[dateKey].originalTimestamp) {
          dateGroups[dateKey] = item;
        }
      });

      // Convert back to array and sort by date
      const uniqueData = Object.values(dateGroups).map(item => {
        const { originalDate, originalTimestamp, ...cleanItem } = item;
        return cleanItem;
      }).sort((a, b) => new Date(a.time) - new Date(b.time));

      const transformedData = uniqueData;

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
  }, [symbol, token]);

  // --------------------------------------------
  // 3. Create Chart and Set Initial Data
  // --------------------------------------------
  useEffect(() => {
    if (!chartData || !chartData.length) return;
    if (!chartContainerRef.current) return;

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

    // SMA lines (filter out null values)
    const sma50Data = seriesData
      .filter((item) => item.sma_50 !== null && item.sma_50 > 0)
      .map((item) => ({
        time: item.time,
        value: item.sma_50,
      }));
    const sma100Data = seriesData
      .filter((item) => item.sma_100 !== null && item.sma_100 > 0)
      .map((item) => ({
        time: item.time,
        value: item.sma_100,
      }));
    const sma200Data = seriesData
      .filter((item) => item.sma_200 !== null && item.sma_200 > 0)
      .map((item) => ({
        time: item.time,
        value: item.sma_200,
      }));

    const ma50Series = chart.addSeries(LineSeries, {
      color: "#3b82f680", // blue-500 with transparency
      lineWidth: 2,
    });
    ma50Series.setData(sma50Data);
    ma50SeriesRef.current = ma50Series;

    const ma100Series = chart.addSeries(LineSeries, {
      color: "#10b98180", // emerald-500 with transparency
      lineWidth: 2,
    });
    ma100Series.setData(sma100Data);
    ma100SeriesRef.current = ma100Series;

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
      !ma100SeriesRef.current ||
      !ma200SeriesRef.current ||
      !lastCandleRef.current
    ) {
      return;
    }

    // Find the tick for this token
    const tick = liveData.find((t) => t.instrument_token === token);
    if (!tick) return;

    // Extract the new price, volume, SMAs from the real-time feed
    // (Adjust the property names if your feed is different)
    const newPrice = tick.last_price;
    const newVolume = tick.volume_traded;
    const newSma50 = tick.sma_50;
    const newSma100 = tick.sma_100;
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

    // If the feed includes updated SMA values, update them too
    // Only update SMA values if they are valid numbers (not undefined, null, or 0 from missing data)
    if (newSma50 !== undefined && newSma50 !== null && newSma50 > 0) {
      updatedCandle.sma_50 = newSma50;
    }
    if (newSma100 !== undefined && newSma100 !== null && newSma100 > 0) {
      updatedCandle.sma_100 = newSma100;
    }
    if (newSma200 !== undefined && newSma200 !== null && newSma200 > 0) {
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
  }, [liveData, chartData, token]);

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

      {/* Full Chart Button (top-right corner) */}
      <button
        onClick={() => openChart(symbol)}
        style={{
          position: "absolute",
          top: "8px",
          right: "8px",
          zIndex: 10,
          backgroundColor: "rgba(39, 39, 42, 0.8)", // zinc-800 with transparency
          color: "#fff",
          padding: "8px 12px",
          borderRadius: "6px",
          border: "1px solid #3f3f46", // zinc-700
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: "6px",
        }}
      >
        <span>Open in TradingView</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="size-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
          />
        </svg>
      </button>
    </Box>
  );
}

export default SideChart;
