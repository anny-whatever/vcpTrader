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
      toast.success(response?.data?.message, { duration: 5000 });
    } catch (error) {
      console.error("Error executing buy order:", error);
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
      <Toaster position="bottom-right" />
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
          Buy {symbol}
        </DialogTitle>
        <DialogContent sx={{ pb: 0.5 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.85rem",
              mb: 1,
            }}
          >
            <Typography variant="body2">
              Available Risk: {AvailableRisk?.toFixed(2)}
            </Typography>
            <Typography variant="body2">
              Used Risk: {UsedRisk?.toFixed(2)}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
            <Typography variant="body2" sx={{ mr: 1 }}>
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
                ".MuiFormControlLabel-label": { fontSize: "0.8rem" },
              }}
            />
          </Box>
          {methodRiskPoolMethod ? (
            <TextField
              label="Risk pool %"
              type="number"
              value={intendedRisk}
              onChange={(e) => setIntendedRisk(e.target.value)}
              variant="filled"
              size="small"
              fullWidth
              InputProps={{ disableUnderline: true }}
              sx={{
                bgcolor: "#27272A",
                width: "60%",
                borderRadius: "12px",
                "& .MuiInputBase-root": { color: "white" },
                "& .MuiInputLabel-root": { color: "white", fontSize: "0.8rem" },
              }}
            />
          ) : (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                mt: 1,
                justifyContent: "space-between",
              }}
            >
              <TextField
                label="Quantity"
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                variant="filled"
                size="small"
                InputProps={{ disableUnderline: true, inputProps: { min: 0 } }}
                sx={{
                  width: "60%",
                  bgcolor: "#27272A",
                  borderRadius: "12px",
                  "& .MuiInputBase-root": { color: "white" },
                  "& .MuiInputLabel-root": {
                    color: "white",
                    fontSize: "0.8rem",
                  },
                }}
              />
              <Typography variant="body2" sx={{ fontSize: "0.85rem" }}>
                Cost: {quantity ? (quantity * ltp).toFixed(2) : 0}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ pt: 0.5 }}>
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
            onClick={() => {
              if (methodRiskPoolMethod) {
                sendBuyOrder(quantity, intendedRisk, ltp, methodRiskPoolMethod);
              } else {
                sendBuyOrder(quantity);
              }
              handleClose();
            }}
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
            Buy
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default BuyModal;
