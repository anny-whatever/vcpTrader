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

function ModifyTgtModal({ isOpen, onClose, symbol, currentTarget }) {
  const [newTarget, setNewTarget] = useState(currentTarget || "");

  const handleModifyTarget = async () => {
    try {
      if (!newTarget) {
        toast.error("Please enter a target value");
        return;
      }

      const response = await api.get(
        `/api/order/modifytarget?symbol=${symbol}&tgt=${newTarget}`
      );
      PlayToastSound();
      toast.success(
        response?.data?.message || "Target modified successfully!",
        {
          duration: 5000,
        }
      );
    } catch (error) {
      PlayErrorSound();
      toast.error("Error modifying target.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
    setNewTarget(currentTarget || "");
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
          Modify Target for {symbol}
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
              Current Target: {currentTarget || "Not set"}
            </Typography>
          </Box>
          <TextField
            label="New Target"
            type="number"
            value={newTarget}
            onChange={(e) => setNewTarget(e.target.value)}
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
              handleModifyTarget();
              handleClose();
            }}
            sx={modalStyles.primaryButton}
          >
            Modify Target
          </Button>
        </DialogActions>
      </Dialog>
      <Toaster position="top-right" richColors />
    </>
  );
}

export default ModifyTgtModal;
