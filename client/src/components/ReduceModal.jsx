import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
} from "@mui/material";
import api from "../utils/api";
import { Toaster, toast } from "sonner";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";
import modalStyles from "./ui/ModalStyles";

function ReduceModal({ isOpen, onClose, symbol, qty }) {
  const [reduceQuantity, setReduceQuantity] = useState("");

  const sendReduceOrder = async (reduceQty) => {
    try {
      if (!reduceQty || reduceQty <= 0) {
        toast.error("Please enter a valid quantity to reduce");
        return;
      }

      if (reduceQty > qty) {
        toast.error("Reduce quantity cannot be greater than position quantity");
        return;
      }

      const response = await api.get(
        `/api/order/reduce?symbol=${symbol}&qty=${reduceQty}`
      );
      PlayToastSound();
      toast.success(
        response?.data?.message || "Reduce order executed successfully!",
        { duration: 5000 }
      );
    } catch (error) {
      PlayErrorSound();
      toast.error("Error executing reduce order.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
    setReduceQuantity("");
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
        <DialogTitle sx={modalStyles.title}>Reduce {symbol}</DialogTitle>
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
              Current Quantity: {qty}
            </Typography>
          </Box>
          <Box sx={{ mt: 1 }}>
            <TextField
              label="Reduce Quantity"
              type="number"
              value={reduceQuantity}
              onChange={(e) => setReduceQuantity(e.target.value)}
              variant="outlined"
              size="small"
              fullWidth
              inputProps={{ min: 1, max: qty }}
              sx={modalStyles.input}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={modalStyles.actions}>
          <Button onClick={handleClose} sx={modalStyles.secondaryButton}>
            Close
          </Button>
          <Button
            onClick={() => {
              sendReduceOrder(reduceQuantity);
              handleClose();
            }}
            sx={modalStyles.primaryButton}
          >
            Reduce
          </Button>
        </DialogActions>
      </Dialog>
      <Toaster position="top-right" richColors />
    </>
  );
}

export default ReduceModal;
