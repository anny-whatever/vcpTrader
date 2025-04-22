import React, { useContext, useState, useEffect } from "react";
import { DataContext } from "../utils/DataContext.jsx";
import { Box, Typography, Paper, useTheme, alpha } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";

const NIFTY_INSTRUMENT_TOKEN = 256265;

const NiftyIndexTicker = () => {
  const theme = useTheme();
  const { liveData } = useContext(DataContext);
  const [niftyData, setNiftyData] = useState(null);

  // For debugging
  useEffect(() => {
    console.log("liveData updated:", liveData);
  }, [liveData]);

  useEffect(() => {
    if (!liveData) return;

    try {
      // Debug the data structure
      console.log("Processing liveData type:", typeof liveData);

      // Handle different potential data formats
      if (typeof liveData === "object") {
        // Case 1: Object with direct key access
        if (liveData[NIFTY_INSTRUMENT_TOKEN]) {
          console.log("Found Nifty data by direct key access");
          setNiftyData(liveData[NIFTY_INSTRUMENT_TOKEN]);
          return;
        }

        // Case 2: Array of ticks
        if (Array.isArray(liveData)) {
          const niftyTick = liveData.find(
            (item) => item.instrument_token === NIFTY_INSTRUMENT_TOKEN
          );
          if (niftyTick) {
            console.log("Found Nifty data in array");
            setNiftyData(niftyTick);
            return;
          }
        }

        // Case 3: Data is in a nested "data" property
        if (liveData.data) {
          if (liveData.data[NIFTY_INSTRUMENT_TOKEN]) {
            console.log("Found Nifty data in nested data object");
            setNiftyData(liveData.data[NIFTY_INSTRUMENT_TOKEN]);
            return;
          }

          if (Array.isArray(liveData.data)) {
            const niftyTick = liveData.data.find(
              (item) => item.instrument_token === NIFTY_INSTRUMENT_TOKEN
            );
            if (niftyTick) {
              console.log("Found Nifty data in nested data array");
              setNiftyData(niftyTick);
              return;
            }
          }
        }
      }

      console.log("Could not locate Nifty data in the provided liveData");
    } catch (error) {
      console.error("Error processing liveData:", error);
    }
  }, [liveData]);

  // Determine color and icon based on percentage change
  let color = theme.palette.text.secondary;
  let Icon = TrendingFlatIcon;
  const percentChange = niftyData?.change_percent || 0;

  if (percentChange > 0) {
    color = theme.palette.success.main;
    Icon = TrendingUpIcon;
  } else if (percentChange < 0) {
    color = theme.palette.error.main;
    Icon = TrendingDownIcon;
  }

  return (
    <Box
      sx={{
        width: "100%",
        backgroundColor: alpha(theme.palette.background.paper, 0.6),
        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.05)}`,
        padding: "4px 0",
        zIndex: 100,
      }}
    >
      <Box
        sx={{
          maxWidth: 1200,
          margin: "0 auto",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Paper
          elevation={0}
          sx={{
            display: "flex",
            alignItems: "center",
            padding: "4px 16px",
            borderRadius: 3,
            backgroundColor: alpha(theme.palette.background.paper, 0.4),
          }}
        >
          <Typography variant="subtitle2" fontWeight={600} mr={1}>
            NIFTY
          </Typography>
          <Typography variant="body2" mr={1}>
            {niftyData?.last_price?.toFixed(2) || "Loading..."}
          </Typography>
          {niftyData ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                color,
              }}
            >
              <Icon fontSize="small" sx={{ marginRight: 0.5 }} />
              <Typography variant="body2" fontWeight={500} color="inherit">
                {percentChange > 0 ? "+" : ""}
                {percentChange.toFixed(2)}%
              </Typography>
            </Box>
          ) : (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                color: theme.palette.text.secondary,
              }}
            >
              <TrendingFlatIcon fontSize="small" sx={{ marginRight: 0.5 }} />
              <Typography variant="body2" fontWeight={500} color="inherit">
                0.00%
              </Typography>
            </Box>
          )}
        </Paper>
      </Box>
    </Box>
  );
};

export default NiftyIndexTicker;
