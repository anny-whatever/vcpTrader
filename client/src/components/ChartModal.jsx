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
import { createChart, BarSeries, ColorType } from "lightweight-charts";
import { Spinner } from "@heroui/react";

// ChartComponent renders the chart using the passed data array.
export const ChartComponent = ({ data }) => {
  const chartContainerRef = useRef();

  useEffect(() => {
    // Helper function to get the container dimensions.
    const getDimensions = () => {
      const container = chartContainerRef.current;
      return {
        width: container.clientWidth,
        height: container.clientHeight - 10,
      };
    };

    // Get initial dimensions.
    const { width, height } = getDimensions();

    // Create the chart using the container's dimensions.
    // Set crosshair mode to 0 for free-moving behavior.
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
      crosshair: {
        mode: 0, // Free moving crosshair (does not snap to data points)
      },
    });

    const seriesData = data || [];

    const newSeries = chart.addSeries(BarSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      thinBars: false,
    });
    newSeries.setData(seriesData);

    // Zoom in if there are more than 50 candles.
    if (seriesData.length > 50) {
      const visibleFrom = seriesData[seriesData.length - 75].time;
      const visibleTo = seriesData[seriesData.length - 1].time;
      chart.timeScale().setVisibleRange({ from: visibleFrom, to: visibleTo });
    } else {
      chart.timeScale().fitContent();
    }

    // Resize handler updates both width and height.
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

  // Ensure the container fills its parent.
  return (
    <div ref={chartContainerRef} style={{ width: "100%", height: "100%" }} />
  );
};

function ChartModal({ isOpen, onClose, symbol, token }) {
  const [chartData, setChartData] = useState(null);

  // Fetch and transform chart data from the API.
  const getChartData = async () => {
    if (symbol && token) {
      try {
        const response = await api.get(
          `/api/data/chartdata?token=${token}&symbol=${symbol}`
        );

        // Fix the date issue by extracting only the date portion.
        const transformedData = response.data.map((item) => ({
          time: item.date.split("T")[0],
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
        }));
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
      onClose={onClose}
      fullWidth
      maxWidth="xl"
      PaperProps={{
        sx: {
          bgcolor: "#18181B",
          color: "white",
          borderRadius: "8px",
          p: 1,
          height: "70vh", // Modal overall height set relative to viewport height.
        },
      }}
    >
      <DialogTitle sx={{ fontSize: "1rem", pb: 0.5 }}>
        Chart for {symbol}
      </DialogTitle>
      <DialogContent
        dividers
        sx={{ p: 0, height: "calc(70vh - 80px)", overflow: "hidden" }} // Adjust content height based on header/actions.
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
          onClick={() => {
            openChart(symbol);
          }}
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
          variant="outlined"
          onClick={onClose}
          sx={{
            color: "#EB455F",
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
