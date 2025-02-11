// src/components/ChartModal.jsx
import React, { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
} from "@mui/material";
import api from "../utils/api";
import {
  createChart,
  BarSeries,
  ColorType,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";

import { createSeriesMarkers } from "lightweight-charts";

import { Spinner } from "@heroui/react";

export const ChartComponent = ({ data, markers }) => {
  const chartContainerRef = useRef();

  useEffect(() => {
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

    const seriesData = data || [];

    // Prepare SMA data series
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

    // Add the main price (bar) series
    const newSeries = chart.addSeries(BarSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      thinBars: false,
    });
    newSeries.setData(seriesData);

    // Add SMA series as line series
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

    // Prepare and add the volume series
    const volumeData = seriesData.map((item) => ({
      time: item.time,
      value: item.volume,
    }));

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#ffffff4b",
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "", // set as an overlay by setting a blank priceScaleId
      scaleMargins: {
        top: 0.7, // highest point will be 70% away from the top
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

    // Set the visible time range if enough data is available
    if (seriesData.length > 75) {
      const visibleFrom = seriesData[seriesData.length - 75].time;
      const visibleTo = seriesData[seriesData.length - 1].time;
      chart.timeScale().setVisibleRange({ from: visibleFrom, to: visibleTo });
    } else {
      chart.timeScale().fitContent();
    }

    // Handle chart container resizing
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
    <div ref={chartContainerRef} style={{ width: "100%", height: "100%" }} />
  );
};

function ChartModal({ isOpen, onClose, symbol, token, markers = [] }) {
  const [chartData, setChartData] = useState(null);

  const getChartData = async () => {
    if (symbol && token) {
      try {
        const response = await api.get(
          `/api/data/chartdata?token=${token}&symbol=${symbol}`
        );
        // Transform the API response to include all needed fields
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

        console.log(transformedData);

        setChartData(transformedData);
      } catch (error) {
        console.error("Error fetching chart data:", error);
      }
    }
  };

  const openChart = (symbol) => {
    window.open(
      `https://www.tradingview.com/chart/?symbol=NSE:${symbol}`,
      "_blank"
    );
  };

  useEffect(() => {
    getChartData();
  }, [symbol, token]);

  return (
    <Dialog
      open={isOpen}
      onClose={() => {
        onClose();
        setChartData(null);
      }}
      fullWidth
      maxWidth="xl"
      PaperProps={{
        sx: {
          bgcolor: "#18181B",
          color: "white",
          borderRadius: "8px",
          p: 1,
          height: "70vh",
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
        className="flex flex-row items-center justify-between "
      >
        <span>Chart for {symbol}</span>
        <Button
          onClick={() => getChartData()}
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
          Refresh Chart
        </Button>
      </DialogTitle>
      <DialogContent
        dividers
        sx={{ p: 0, height: "calc(70vh - 80px)", overflow: "hidden" }}
      >
        {chartData ? (
          <ChartComponent data={chartData} markers={markers} />
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
          onClick={() => {
            onClose();
            setChartData(null);
          }}
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
