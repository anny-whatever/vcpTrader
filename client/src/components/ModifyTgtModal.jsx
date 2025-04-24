import React, { useState, useEffect } from "react";
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

function ModifyTgtModal({ isOpen, onClose, symbol, currentEntryPrice, currentTarget }) {
  const [newTarget, setNewTarget] = useState(currentTarget || "");
  const [usePercentage, setUsePercentage] = useState(false);
  const [percentageValue, setPercentageValue] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  // Calculate and update target when entry price or percentage changes
  useEffect(() => {
    if (!isEditing && usePercentage && percentageValue && currentEntryPrice) {
      // Calculate target based on percentage above entry price
      const percentage = parseFloat(percentageValue) / 100;
      const calculatedTarget = currentEntryPrice * (1 + percentage);
      setNewTarget(calculatedTarget.toFixed(2));
    }
  }, [usePercentage, percentageValue, currentEntryPrice, isEditing]);

  // Update percentage when absolute value changes
  useEffect(() => {
    if (!isEditing && !usePercentage || !newTarget || !currentEntryPrice) return;
    
    const targetValue = parseFloat(newTarget);
    const entryPrice = parseFloat(currentEntryPrice);
    const percentageDiff = ((targetValue - entryPrice) / entryPrice) * 100;
    
    if (!isNaN(percentageDiff)) {
      setPercentageValue(Math.round(percentageDiff));
    }
  }, [newTarget, currentEntryPrice, usePercentage, isEditing]);

  const handleModifyTarget = async () => {
    try {
      if (!newTarget) {
        toast.error("Please enter a target value");
        return;
      }

      const response = await api.get(
        `/api/order/change_tgt?symbol=${symbol}&tgt=${newTarget}`
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
    setPercentageValue("");
    setUsePercentage(false);
  };

  const handlePercentageChange = (e) => {
    setIsEditing(true);
    const value = e.target.value;
    // Store percentage as integer (no decimals)
    setPercentageValue(value);
    
    if (currentEntryPrice && value) {
      const percentage = parseInt(value, 10) / 100;
      const calculatedTarget = currentEntryPrice * (1 + percentage);
      setNewTarget(calculatedTarget.toFixed(2));
    }
    setIsEditing(false);
  };

  const handleAbsoluteChange = (e) => {
    setIsEditing(true);
    const value = e.target.value;
    setNewTarget(value);
    
    if (usePercentage && currentEntryPrice && value) {
      const targetValue = parseFloat(value);
      const entryPrice = parseFloat(currentEntryPrice);
      const percentageDiff = ((targetValue - entryPrice) / entryPrice) * 100;
      
      if (!isNaN(percentageDiff)) {
        setPercentageValue(Math.round(percentageDiff));
      }
    }
    setIsEditing(false);
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
              Current Entry: {currentEntryPrice ? currentEntryPrice.toFixed(2) : "Not set"}
            </Typography>
            <Typography variant="body2" sx={{ color: "#f4f4f5" }}>
              Current Target: {currentTarget || "Not set"}
            </Typography>
          </Box>
          
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <Typography variant="body2" sx={{ mr: 1, color: "#f4f4f5" }}>
              Target
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={usePercentage}
                  onChange={(e) => setUsePercentage(e.target.checked)}
                  color="primary"
                  size="small"
                />
              }
              label="Use Percentage"
              sx={{
                m: 0,
                ".MuiFormControlLabel-label": {
                  fontSize: "0.85rem",
                  color: "#a1a1aa",
                },
              }}
            />
          </Box>
          
          {usePercentage ? (
            <TextField
              label="Target Percentage (%)"
              type="number"
              value={percentageValue}
              onChange={handlePercentageChange}
              variant="outlined"
              size="small"
              fullWidth
              sx={modalStyles.input}
              InputProps={{
                inputProps: { 
                  min: 0,
                  step: 1
                }
              }}
            />
          ) : (
            <TextField
              label="Absolute Target"
              type="number"
              value={newTarget}
              onChange={handleAbsoluteChange}
              variant="outlined"
              size="small"
              fullWidth
              sx={modalStyles.input}
            />
          )}
          
          {usePercentage && newTarget && (
            <Typography variant="body2" sx={{ mt: 1, color: "#f4f4f5", fontSize: "0.85rem" }}>
              Calculated Target: {newTarget} ({percentageValue}%)
            </Typography>
          )}
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
    </>
  );
}

export default ModifyTgtModal;
