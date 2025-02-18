// src/components/ChartModal.jsx
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

/**
 * ChartComponent:
 * Renders a daily bar chart with SMAs and volume histogram.
 */
export const ChartComponent = ({ data }) => {
  const chartContainerRef = useRef();

  useEffect(() => {
    if (!data || !data.length) return;
    if (!chartContainerRef.current) return;

    const getDimensions = () => {
      const container = chartContainerRef.current;
      return {
        width: container.clientWidth,
        height: container.clientHeight - 10,
      };
    };

    const { width, height } = getDimensions();

    const chart = createChart(chartContainerRef.current, {
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

    const seriesData = data;

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

    const barSeries = chart.addSeries(BarSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      thinBars: false,
    });
    barSeries.setData(seriesData);

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

    if (seriesData.length > 75) {
      const fromIdx = seriesData.length - 75;
      chart.timeScale().setVisibleRange({
        from: seriesData[fromIdx].time,
        to: seriesData[seriesData.length - 1].time,
      });
    } else {
      chart.timeScale().fitContent();
    }

    const handleResize = () => {
      const { width, height } = getDimensions();
      chart.applyOptions({ width, height });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return (
    <div
      ref={chartContainerRef}
      style={{ width: "100%", height: "100%", minHeight: 300 }}
    />
  );
};

/**
 * ChartModal:
 * - Fetches daily candle data (including SMAs) from the backend.
 * - Displays a spinner while loading.
 * - Updates the last candle in real-time if the market is open.
 * - Renders full screen (vertically and horizontally) on phone view (md breakpoint and below).
 */
function ChartModal({ isOpen, onClose, symbol, token }) {
  const { liveData } = useContext(DataContext);
  const [chartData, setChartData] = useState(null);

  // Use theme and media query: fullScreen for screens md and below.
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));

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

  const openChart = (symbol) => {
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}`,
      "_blank"
    );
  };

  useEffect(() => {
    if (isOpen) {
      getChartData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, symbol, token]);

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
          height: fullScreen ? "100%" : "70vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          fontSize: "1rem",
          pb: 0.5,
          flex: 1,
          items: "center",
          justifyContent: "space-between",
          width: "100%",
        }}
        className="flex flex-row items-center justify-between"
      >
        <Typography variant="h6" component="span">
          Chart for {symbol}
        </Typography>
      </DialogTitle>

      <DialogContent
        dividers
        sx={{
          p: 0,
          height: fullScreen ? "calc(100% - 80px)" : "calc(70vh - 80px)",
          overflow: "hidden",
        }}
      >
        {chartData ? (
          <ChartComponent data={chartData} />
        ) : (
          <Box sx={{ p: 2 }}>
            <div className="flex flex-col items-center justify-center w-full h-[55vh]">
              <Spinner size="lg" />
              <span className="m-5 text-2xl">Loading Chart Data</span>
            </div>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ pt: 0.5 }}>
        <Button
          onClick={() => openChart(symbol)}
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
