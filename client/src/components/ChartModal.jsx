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
import { Spinner } from "@heroui/react";

function ChartModal({ isOpen, onClose, symbol, token }) {
  const { liveData } = useContext(DataContext);
  const [chartData, setChartData] = useState(null);
  const [liveChange, setLiveChange] = useState(null);
  const [OHLC, setOHLC] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
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
    if (isOpen) {
      getChartData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, symbol, token]);

  // --------------------------------------------
  // 2. Create the chart (or update series if already created)
  // --------------------------------------------
  useEffect(() => {
    if (!chartData || !chartData.length) return;
    if (!chartContainerRef.current) return;

    // If the chart already exists, update the series data (without re-creating)
    if (chartRef.current) {
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
      return;
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

    // Main bar series (candlestick-like)
    const barSeries = chart.addSeries(BarSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
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
      color: "#ffffff4b",
      priceFormat: { type: "volume" },
      priceScaleId: "",
      scaleMargins: { top: 0.7, bottom: 0 },
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.7, bottom: 0 },
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
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}`,
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
          bgcolor: "#18181B",
          color: "white",
          borderRadius: "8px",
          p: 1,
          height: fullScreen ? "100%" : "80vh",
        },
      }}
    >
      <DialogContent
        dividers
        sx={{
          p: 0,
          height: fullScreen ? "calc(100% - 80px)" : "calc(70vh - 80px)",
          overflow: "hidden",
        }}
      >
        {!chartData && (
          <Box sx={{ p: 2 }}>
            <div className="flex flex-col items-center justify-center w-full  h-[75vh]">
              <Spinner size="lg" />
              <span className="m-5 text-2xl">Loading Chart Data</span>
            </div>
          </Box>
        )}
        <div
          style={{
            position: "absolute",
            top: "16px",
            left: "16px",
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
            <span
              className={liveChange > 0 ? "text-green-500" : "text-red-500"}
            >
              {liveChange?.toFixed(2)}%
            </span>
          </div>
          <div className="flex flex-wrap gap-2 ">
            <span>O: {OHLC?.open?.toFixed(2)}</span>
            <span>H: {OHLC?.high?.toFixed(2)}</span>
            <span>L: {OHLC?.low?.toFixed(2)}</span>
            <span>C: {livePrice?.toFixed(2)}</span>
          </div>
        </div>
        <div
          ref={chartContainerRef}
          style={{ width: "100%", height: "100%" }}
        />
      </DialogContent>
      <DialogActions sx={{ pt: 0.5 }}>
        <Button
          onClick={() => openFullChart(symbol)}
          variant="text"
          sx={{
            color: "#EB455F",
            borderRadius: "12px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: "0.85rem",
          }}
        >
          Open full chart
        </Button>
        <Button
          onClick={getChartData}
          variant="contained"
          color="warning"
          sx={{
            color: "#ffffff",
            borderRadius: "12px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: "0.85rem",
          }}
        >
          Refresh
        </Button>
        <Button
          onClick={onClose}
          variant="contained"
          color="error"
          sx={{
            color: "#ffffff",
            borderRadius: "12px",
            textTransform: "none",
            fontWeight: "normal",
            fontSize: "0.85rem",
          }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default ChartModal;
