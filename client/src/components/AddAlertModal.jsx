// src/components/AddAlertModal.jsx
import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Box,
  Typography,
} from "@mui/material";
import api from "../utils/api";
import { Toaster, toast } from "sonner";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";

function AddAlertModal({ isOpen, onClose, symbol, instrument_token, ltp }) {
  // Pre-populate the alert price with ltp, but allow editing
  const [price, setPrice] = useState("");
  const [alertType, setAlertType] = useState("target"); // default to target

  // When ltp changes, update the price field
  useEffect(() => {
    setPrice(ltp || "");
  }, [ltp]);

  const handleSubmit = async () => {
    if (!price || !alertType) {
      toast.error("Please fill all fields", { duration: 5000 });
      return;
    }
    try {
      const payload = {
        instrument_token: instrument_token,
        symbol: symbol,
        price: parseFloat(price),
        alert_type: alertType,
      };
      const response = await api.post("/api/alerts/add", payload);
      PlayToastSound();
      toast.success(response?.data?.message || "Alert added successfully", {
        duration: 5000,
      });
      onClose();
    } catch (error) {
      console.error("Error adding alert:", error);
      PlayErrorSound();
      toast.error(
        (error?.response && error?.response?.data?.message) ||
          "Failed to add alert",
        { duration: 5000 }
      );
    }
  };

  const handleClose = () => {
    onClose();
    setAlertType("target");
  };

  return (
    <>
      <Dialog
        open={isOpen}
        onClose={handleClose}
        fullWidth
        maxWidth="xs"
        PaperProps={{
          sx: {
            bgcolor: "#18181B",
            color: "white",
            backdropFilter: "blur(8px)",
            borderRadius: "8px",
            p: 1,
          },
        }}
      >
        <DialogTitle sx={{ fontSize: "1rem", pb: 0.5 }}>
          Add Alert for {symbol}
        </DialogTitle>
        <DialogContent sx={{ pb: 0.5 }}>
          {/* Single-line display for Instrument Token and LTP */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.85rem",
              mb: 1,
            }}
          >
            <Typography variant="body2">Token: {instrument_token}</Typography>
            <Typography variant="body2">
              LTP:{" "}
              {ltp && typeof ltp === "number" ? ltp.toFixed(2) : ltp || "N/A"}
            </Typography>
          </Box>
          {/* Single row for input fields */}
          <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
            <TextField
              label="Alert Price"
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              variant="filled"
              size="small"
              fullWidth
              InputProps={{ disableUnderline: true }}
              sx={{
                bgcolor: "#27272A",
                borderRadius: "12px",
                "& .MuiInputBase-root": { color: "white" },
                "& .MuiInputLabel-root": { color: "white", fontSize: "0.8rem" },
              }}
            />
            <TextField
              select
              label="Type"
              value={alertType}
              onChange={(e) => setAlertType(e.target.value)}
              variant="filled"
              size="small"
              sx={{
                bgcolor: "#27272A",
                borderRadius: "12px",
                minWidth: "100px",
                "& .MuiInputBase-root": { color: "white" },
                "& .MuiInputLabel-root": { color: "white", fontSize: "0.8rem" },
              }}
            >
              <MenuItem value="target">Target</MenuItem>
              <MenuItem value="sl">Stop Loss</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions sx={{ pt: 0.5, justifyContent: "flex-end" }}>
          <Button
            onClick={handleClose}
            variant="text"
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
          <Button
            onClick={handleSubmit}
            variant="contained"
            sx={{
              bgcolor: "#2DD4BF",
              "&:hover": { bgcolor: "#26BFAE" },
              color: "black",
              borderRadius: "12px",
              textTransform: "none",
              fontWeight: "normal",
              fontSize: "0.85rem",
            }}
          >
            Add Alert
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default AddAlertModal;
