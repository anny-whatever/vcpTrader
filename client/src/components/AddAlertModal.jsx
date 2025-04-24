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
import modalStyles from "./ui/ModalStyles";

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
          sx: modalStyles.paper,
        }}
      >
        <DialogTitle sx={modalStyles.title}>Add Alert for {symbol}</DialogTitle>
        <DialogContent sx={modalStyles.content}>
          {/* Single-line display for Instrument Token and LTP */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.85rem",
              mb: 2,
            }}
          >
            <Typography variant="body2" sx={{ color: "#f4f4f5" }}>
              Token: {instrument_token}
            </Typography>
            <Typography variant="body2" sx={{ color: "#f4f4f5" }}>
              LTP:{" "}
              {ltp && typeof ltp === "number" ? ltp.toFixed(2) : ltp || "N/A"}
            </Typography>
          </Box>
          {/* Single row for input fields */}
          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            <TextField
              label="Alert Price"
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              variant="outlined"
              size="small"
              fullWidth
              sx={modalStyles.input}
            />
            <TextField
              select
              label="Type"
              value={alertType}
              onChange={(e) => setAlertType(e.target.value)}
              variant="outlined"
              size="small"
              sx={{
                ...modalStyles.input,
                minWidth: "100px",
              }}
            >
              <MenuItem value="target">Target</MenuItem>
              <MenuItem value="sl">Stop Loss</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions sx={modalStyles.actions}>
          <Button onClick={handleClose} sx={modalStyles.secondaryButton}>
            Close
          </Button>
          <Button onClick={handleSubmit} sx={modalStyles.primaryButton}>
            Add Alert
          </Button>
        </DialogActions>
      </Dialog>
      
    </>
  );
}

export default AddAlertModal;
