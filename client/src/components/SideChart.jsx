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
import { Spinner } from "@heroui/react";

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
  const ma150SeriesRef = useRef(null);
  const ma200SeriesRef = useRef(null);

  // Reference to track the last candle we’re updating
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
      const response = await api.get(
        `/api/data/chartdata?token=${token}&symbol=${symbol}`
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
        background: { type: ColorType.Solid, color: "#181818" },
        textColor: "#d1d4dc",
      },
      width,
      height,
      grid: {
        vertLines: { color: "#363c4e" },
        horzLines: { color: "#363c4e" },
      },
      crosshair: { mode: 0 },
    });
    chartRef.current = chart;

    const seriesData = chartData;

    // Main Bar Series (candlestick-like)
    const barSeries = chart.addSeries(BarSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
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
      color: "#ffffff4b",
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
      color: "#2962ff62",
      lineWidth: 2,
    });
    ma50Series.setData(sma50Data);
    ma50SeriesRef.current = ma50Series;

    const ma150Series = chart.addSeries(LineSeries, {
      color: "#3bfa2d4b",
      lineWidth: 2,
    });
    ma150Series.setData(sma150Data);
    ma150SeriesRef.current = ma150Series;

    const ma200Series = chart.addSeries(LineSeries, {
      color: "#fa642d4b",
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
    // (Adjust the property names if your feed is different)
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
      }}
    >
      {/* Chart Container */}
      <div ref={chartContainerRef} style={{ width: "100%", height: "100%" }} />

      {/* Full Chart Button (top-right corner) */}
      <div
        style={{
          position: "absolute",
          top: "8px",
          left: "8px",
          zIndex: 10,
          backgroundColor: "#2c2c2e4D",
          color: "#fff",
          padding: "6px 10px",
          borderRadius: "4px",
          border: "none",
          cursor: "pointer",
          fontSize: "0.9rem",
          marginRight: "60px",
        }}
        className="flex flex-col justify-center items-left"
      >
        <span>Symbol: {symbol}</span>

        <div>
          Change:{" "}
          <span className={liveChange > 0 ? "text-green-500" : "text-red-500"}>
            {liveChange?.toFixed(2)}%
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <span>O: {OHLC?.open?.toFixed(2)}</span>
          <span>H: {OHLC?.high?.toFixed(2)}</span>
          <span>L: {OHLC?.low?.toFixed(2)}</span>
          <span>C: {livePrice?.toFixed(2)}</span>
        </div>
      </div>
      <button
        onClick={() => openChart(symbol)}
        style={{
          position: "absolute",
          top: "8px",
          right: "8px",
          zIndex: 10,
          backgroundColor: "#2c2c2e4D",
          color: "#fff",
          padding: "6px 10px",
          borderRadius: "4px",
          border: "none",
          cursor: "pointer",
          fontSize: "0.9rem",
          marginRight: "60px",
        }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="size-6"
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
