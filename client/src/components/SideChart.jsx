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
  const chartContainerRef = useRef();

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

  useEffect(() => {
    if (symbol && token) {
      getChartData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, token]);

  // --------------------------------------------
  // 3. Real-time Updates
  // --------------------------------------------
  useEffect(() => {
    if (!liveData || !liveData.length || !chartData || !chartData.length)
      return;

    const tick = liveData.find((t) => t.instrument_token === token);
    if (!tick) return;

    setChartData((prevData) => {
      if (!prevData || !prevData.length) return prevData;
      const newData = [...prevData];
      const lastIndex = newData.length - 1;
      const lastBar = { ...newData[lastIndex] };

      const todayStr = new Date().toISOString().split("T")[0];
      if (lastBar.time === todayStr) {
        const newClose = tick.last_price;
        if (newClose > lastBar.high) lastBar.high = newClose;
        if (newClose < lastBar.low) lastBar.low = newClose;
        lastBar.close = newClose;

        if (tick.volume) {
          lastBar.volume = tick.volume;
        }
        newData[lastIndex] = lastBar;
      }
      return newData;
    });
  }, [liveData, chartData, token]);

  // --------------------------------------------
  // 4. Render the Chart
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

    const seriesData = chartData;

    // Main Bar Series
    const barSeries = chart.addSeries(BarSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      thinBars: false,
    });
    barSeries.setData(seriesData);

    // Volume Series
    const volumeData = seriesData.map((item) => ({
      time: item.time,
      value: item.volume,
    }));
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#ffffff4b",
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "",
      scaleMargins: {
        top: 0.7,
        bottom: 0,
      },
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.7,
        bottom: 0,
      },
    });
    volumeSeries.setData(volumeData);

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

    const ma150Series = chart.addSeries(LineSeries, {
      color: "#3bfa2d4b",
      lineWidth: 2,
    });
    ma150Series.setData(sma150Data);

    const ma200Series = chart.addSeries(LineSeries, {
      color: "#fa642d4b",
      lineWidth: 2,
    });
    ma200Series.setData(sma200Data);

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

    // Handle resize
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
      <button
        onClick={() => openChart(symbol)}
        style={{
          position: "absolute",
          top: "8px",
          right: "8px",
          zIndex: 10,
          backgroundColor: "#2c2c2e",
          color: "#fff",
          padding: "6px 10px",
          borderRadius: "4px",
          border: "none",
          cursor: "pointer",
          fontSize: "0.9rem",
          marginRight: "60px",
        }}
      >
        Open Full Chart
      </button>
    </Box>
  );
}

export default SideChart;
