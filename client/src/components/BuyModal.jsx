// src/components/BuyModal.jsx
import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Switch,
  FormControlLabel,
  Box,
  Typography,
} from "@mui/material";
import api from "../utils/api";
import { Toaster, toast } from "sonner";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";
import modalStyles from "./ui/ModalStyles";

function BuyModal({ isOpen, onClose, AvailableRisk, UsedRisk, symbol, ltp }) {
  const [quantity, setQuantity] = useState("");
  const [intendedRisk, setIntendedRisk] = useState("");
  const [methodRiskPoolMethod, setMethodRiskPoolMethod] = useState(false);

  const calculateQtyForRiskPool = (intendedRisk, ltp) => {
    const absoluteRisk =
      (AvailableRisk + UsedRisk) * (parseInt(intendedRisk, 10) / 100);
    const sl = ltp - ltp * 0.1;
    const slPoints = ltp - sl;
    let qty = absoluteRisk / slPoints;
    return Math.round(qty);
  };

  const sendBuyOrder = async (
    qty = 0,
    intendedRisk = 0,
    ltp = 0,
    methodRiskPoolMethod = false
  ) => {
    if (methodRiskPoolMethod) {
      qty = calculateQtyForRiskPool(intendedRisk, ltp);
    }
    try {
      const response = await api.get(
        `/api/order/buy?symbol=${symbol}&qty=${qty}`
      );
      PlayToastSound();
      toast.success(response?.data?.message, { duration: 5000 });
    } catch (error) {
      PlayErrorSound();
      toast.error(
        (error?.response && error?.response?.data?.message) ||
          "Buy order failed",
        { duration: 5000 }
      );
    }
  };

  const handleClose = () => {
    onClose();
    setIntendedRisk("");
    setQuantity("");
    setMethodRiskPoolMethod(false);
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
        <DialogTitle sx={modalStyles.title}>Buy {symbol}</DialogTitle>
        <DialogContent sx={modalStyles.content}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.85rem",
              mb: 2,
            }}
          >
            <Typography variant="body2" sx={{ color: "#f4f4f5" }}>
              Available Risk: {AvailableRisk?.toFixed(2)}
            </Typography>
            <Typography variant="body2" sx={{ color: "#f4f4f5" }}>
              Used Risk: {UsedRisk?.toFixed(2)}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <Typography variant="body2" sx={{ mr: 1, color: "#f4f4f5" }}>
              Quantity
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={methodRiskPoolMethod}
                  onChange={(e) => setMethodRiskPoolMethod(e.target.checked)}
                  color="primary"
                  size="small"
                />
              }
              label="Risk pool %"
              sx={{
                m: 0,
                ".MuiFormControlLabel-label": {
                  fontSize: "0.85rem",
                  color: "#a1a1aa",
                },
              }}
            />
          </Box>
          {methodRiskPoolMethod ? (
            <TextField
              label="Risk pool %"
              type="number"
              value={intendedRisk}
              onChange={(e) => setIntendedRisk(e.target.value)}
              variant="outlined"
              size="small"
              fullWidth
              sx={modalStyles.input}
            />
          ) : (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 2,
                justifyContent: "space-between",
              }}
            >
              <TextField
                label="Quantity"
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                variant="outlined"
                size="small"
                inputProps={{ min: 0 }}
                sx={{ ...modalStyles.input, width: "60%" }}
              />
              <Typography
                variant="body2"
                sx={{ fontSize: "0.9rem", color: "#f4f4f5" }}
              >
                Cost: {quantity ? (quantity * ltp).toFixed(2) : 0}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={modalStyles.actions}>
          <Button onClick={handleClose} sx={modalStyles.secondaryButton}>
            Close
          </Button>
          <Button
            onClick={() => {
              if (methodRiskPoolMethod) {
                sendBuyOrder(quantity, intendedRisk, ltp, methodRiskPoolMethod);
              } else {
                sendBuyOrder(quantity);
              }
              handleClose();
            }}
            sx={modalStyles.successButton}
          >
            Buy
          </Button>
        </DialogActions>
      </Dialog>
      
    </>
  );
}

export default BuyModal;
