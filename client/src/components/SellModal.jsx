import React from "react";
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
import { Toaster, toast } from "sonner";

function SellModal({ isOpen, onClose, AvailableRisk, UsedRisk, symbol }) {
  const sendSellOrder = async () => {
    try {
      const response = await api.get(`/api/order/exit?symbol=${symbol}`);
      toast.success(
        response?.data?.message || "Sell order executed successfully!",
        { duration: 5000 }
      );
    } catch (error) {
      console.error("Error executing sell order:", error);
      toast.error("Error executing sell order.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
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
          Exit {symbol}
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
              sendSellOrder();
              handleClose();
            }}
            variant="contained"
            sx={{
              bgcolor: "#EB455F",
              "&:hover": { bgcolor: "#e03d56" },
              color: "white",
              borderRadius: "12px",
              textTransform: "none",
              fontWeight: "normal",
              fontSize: "0.85rem",
            }}
          >
            Sell
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default SellModal;
