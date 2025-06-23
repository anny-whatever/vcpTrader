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
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";
import modalStyles from "./ui/ModalStyles";

function SellModal({ isOpen, onClose, AvailableRisk, UsedRisk, symbol }) {
  const sendSellOrder = async () => {
    try {
      const encodedSymbol = encodeURIComponent(symbol).replace(/&/g, '%26');
      const response = await api.get(`/api/order/exit?symbol=${encodedSymbol}`);

      PlayToastSound();
      toast.success(
        response?.data?.message || "Sell order executed successfully!",
        { duration: 5000 }
      );
    } catch (error) {
      PlayErrorSound();
      toast.error("Error executing sell order.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
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
        <DialogTitle sx={modalStyles.title}>Exit {symbol}</DialogTitle>
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
          <Typography
            variant="body2"
            sx={{ color: "#f4f4f5", textAlign: "center", mt: 1 }}
          >
            Are you sure you want to exit this position?
          </Typography>
        </DialogContent>
        <DialogActions sx={modalStyles.actions}>
          <Button onClick={handleClose} sx={modalStyles.secondaryButton}>
            Close
          </Button>
          <Button
            onClick={() => {
              sendSellOrder();
              handleClose();
            }}
            sx={modalStyles.dangerButton}
          >
            Sell
          </Button>
        </DialogActions>
      </Dialog>
      
    </>
  );
}

export default SellModal;
