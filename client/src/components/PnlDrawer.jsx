// PnlDrawer.jsx
import React, { useState, useContext, useEffect } from "react";
import { DataContext } from "../utils/DataContext";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode";
import {
  Paper,
  Typography,
  Box,
  IconButton,
  alpha,
  styled,
} from "@mui/material";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { motion } from "framer-motion";

const DrawerContainer = styled(motion.div)(({ theme }) => ({
  position: "fixed",
  bottom: theme.spacing(4),
  right: theme.spacing(4),
  zIndex: 1000,
  borderRadius: theme.shape.borderRadius * 2,
  boxShadow: "0 8px 32px rgba(0, 0, 0, 0.25)",
  overflow: "hidden",
  backdropFilter: "blur(8px)",
}));

const DrawerPaper = styled(Paper)(({ theme, open }) => ({
  backgroundColor: alpha(theme.palette.background.paper, 0.85),
  transition: theme.transitions.create(["width", "padding"], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.standard,
  }),
  width: open ? 250 : 56,
  padding: open ? theme.spacing(2) : theme.spacing(1),
}));

const ToggleButton = styled(IconButton)(({ theme }) => ({
  position: "absolute",
  right: theme.spacing(0.5),
  top: theme.spacing(0.5),
}));

const PnlDrawer = () => {
  const { positions, liveData } = useContext(DataContext);
  const { token, multiplierEnabled } = useContext(AuthContext);
  const [isOpen, setIsOpen] = useState(true);
  const [totalPnl, setTotalPnl] = useState(0);
  const [capitalUsed, setCapitalUsed] = useState(0);

  // Determine multiplier based on user role and toggle
  let multiplier = 1;
  if (token) {
    try {
      const decoded = jwtDecode(token);
      const userRole = decoded.role || "";
      // For admin users, use the toggle setting. For non-admin users, always use multiplier
      if (userRole === "admin") {
        multiplier = multiplierEnabled ? 25 : 1;
      } else {
        multiplier = 25; // Non-admin users always have multiplier
      }
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // Merge liveData into positions just like in AllPositions
  useEffect(() => {
    if (positions && liveData) {
      positions.forEach((pos) => {
        const liveItem = liveData.find(
          (item) => item.instrument_token === pos.token
        );
        if (liveItem) {
          pos.last_price = liveItem.last_price;
        }
      });
    }
  }, [positions, liveData]);

  // Compute total P&L and capital used based on updated positions
  useEffect(() => {
    if (positions) {
      let runningPnl = 0;
      let runningCap = 0;
      positions.forEach((pos) => {
        runningPnl +=
          (pos.last_price - pos.entry_price) * pos.current_qty + pos.booked_pnl;
        runningCap += pos.entry_price * pos.current_qty;
      });
      setTotalPnl(runningPnl);
      setCapitalUsed(runningCap);
    }
  }, [positions, liveData, multiplierEnabled]);

  // Animation variants for the drawer
  const variants = {
    open: {
      width: 250,
      transition: {
        type: "spring",
        stiffness: 500,
        damping: 30,
      },
    },
    closed: {
      width: 56,
      transition: {
        type: "spring",
        stiffness: 500,
        damping: 30,
      },
    },
  };

  return (
    <DrawerContainer
      initial="open"
      animate={isOpen ? "open" : "closed"}
      variants={variants}
    >
      <DrawerPaper open={isOpen} elevation={6}>
        <ToggleButton
          size="small"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? "Hide P&L drawer" : "Show P&L drawer"}
        >
          {isOpen ? (
            <ChevronRightIcon fontSize="small" />
          ) : (
            <ChevronLeftIcon fontSize="small" />
          )}
        </ToggleButton>

        <Box
          mt={isOpen ? 2 : 0}
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          {!isOpen ? (
            <Typography
              variant="button"
              sx={{
                transform: "rotate(-90deg)",
                whiteSpace: "nowrap",
                color: totalPnl >= 0 ? "success.main" : "error.main",
                fontWeight: "bold",
                marginRight: "20px",
              }}
            >
              P&L
            </Typography>
          ) : (
            <Box width="100%" mt={2}>
              <Typography variant="caption" color="text.secondary">
                Total P&L
              </Typography>
              <Box display="flex" alignItems="baseline" mt={0.5}>
                <Typography
                  variant="h6"
                  sx={{
                    color: totalPnl >= 0 ? "success.main" : "error.main",
                    fontWeight: "bold",
                  }}
                >
                  {(totalPnl * multiplier).toFixed(2)}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ ml: 1 }}
                >
                  (
                  {capitalUsed === 0
                    ? "0.00"
                    : ((totalPnl / capitalUsed) * 100).toFixed(2)}
                  %)
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
      </DrawerPaper>
    </DrawerContainer>
  );
};

export default PnlDrawer;
