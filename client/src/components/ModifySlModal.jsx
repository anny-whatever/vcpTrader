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

function ModifySlModal({ isOpen, onClose, symbol, currentSl }) {
  const [newSl, setNewSl] = useState(currentSl || "");

  const handleModifySl = async () => {
    try {
      if (!newSl) {
        toast.error("Please enter a stop loss value");
        return;
      }

      const response = await api.get(
        `/api/order/modifysl?symbol=${symbol}&sl=${newSl}`
      );
      PlayToastSound();
      toast.success(
        response?.data?.message || "Stop loss modified successfully!",
        {
          duration: 5000,
        }
      );
    } catch (error) {
      PlayErrorSound();
      toast.error("Error modifying stop loss.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
    setNewSl(currentSl || "");
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
        <DialogTitle sx={modalStyles.title}>
          Modify Stop Loss for {symbol}
        </DialogTitle>
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
              Current Stop Loss: {currentSl || "Not set"}
            </Typography>
          </Box>
          <TextField
            label="New Stop Loss"
            type="number"
            value={newSl}
            onChange={(e) => setNewSl(e.target.value)}
            variant="outlined"
            size="small"
            fullWidth
            sx={modalStyles.input}
          />
        </DialogContent>
        <DialogActions sx={modalStyles.actions}>
          <Button onClick={handleClose} sx={modalStyles.secondaryButton}>
            Close
          </Button>
          <Button
            onClick={() => {
              handleModifySl();
              handleClose();
            }}
            sx={modalStyles.dangerButton}
          >
            Modify SL
          </Button>
        </DialogActions>
      </Dialog>
      <Toaster position="top-right" richColors />
    </>
  );
}

export default ModifySlModal;
