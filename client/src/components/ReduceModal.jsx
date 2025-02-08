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

function ReduceModal({
  isOpen,
  onClose,
  symbol,
  ltp,
  AvailableRisk,
  UsedRisk,
  currentQuantity,
}) {
  const [quantity, setQuantity] = useState("");
  const [qtyPercentage, setQtyPercentage] = useState("");
  const [methodPercentage, setMethodPercentageMethod] = useState(false);

  const calculateQtyForPercentage = (qtyPercentage) => {
    let qty = (parseInt(qtyPercentage, 10) / 100) * currentQuantity;
    return Math.round(qty);
  };

  const sendReduceOrder = async (qty = 0, methodPercentage = false) => {
    if (methodPercentage) {
      qty = calculateQtyForPercentage(qtyPercentage);
    }
    try {
      const response = await api.get(
        `/api/order/reduce?symbol=${symbol}&qty=${qty}`
      );
      toast.success(
        response?.data?.message || "Reduce order executed successfully!",
        { duration: 5000 }
      );
    } catch (error) {
      console.error("Error executing reduce order:", error);
      toast.error("Error executing reduce order.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
    setQtyPercentage("");
    setQuantity("");
    setMethodPercentageMethod(false);
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
          Reduce {symbol}
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
                  checked={methodPercentage}
                  onChange={(e) => setMethodPercentageMethod(e.target.checked)}
                  color="primary"
                  size="small"
                />
              }
              label="Quantity %"
              sx={{
                m: 0,
                ".MuiFormControlLabel-label": { fontSize: "0.8rem" },
              }}
            />
          </Box>
          {methodPercentage ? (
            <TextField
              label="Qty percentage %"
              type="number"
              variant="filled"
              size="small"
              value={qtyPercentage}
              onChange={(e) => setQtyPercentage(e.target.value)}
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
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
              <TextField
                label="Quantity"
                type="number"
                variant="filled"
                size="small"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                InputProps={{ disableUnderline: true }}
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
              if (methodPercentage) {
                sendReduceOrder(quantity, methodPercentage);
              } else {
                sendReduceOrder(quantity);
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
            Reduce
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default ReduceModal;
