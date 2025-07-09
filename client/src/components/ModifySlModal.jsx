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

function ModifySlModal({ isOpen, onClose, symbol, currentEntryPrice, currentSl }) {
  const [newSl, setNewSl] = useState(currentSl || "");
  const [usePercentage, setUsePercentage] = useState(false);
  const [percentageValue, setPercentageValue] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  // Calculate and update SL when entry price or percentage changes
  useEffect(() => {
    if (!isEditing && usePercentage && percentageValue && currentEntryPrice) {
      // Calculate SL based on percentage below entry price
      const percentageNum = parseFloat(percentageValue);
      if (!isNaN(percentageNum) && percentageNum >= 0) {
        const percentage = percentageNum / 100;
        const calculatedSL = currentEntryPrice * (1 - percentage);
        setNewSl(calculatedSL.toFixed(2));
      }
    }
  }, [usePercentage, percentageValue, currentEntryPrice, isEditing]);

  // Update percentage when absolute value changes
  useEffect(() => {
    if (!isEditing && !usePercentage || !newSl || !currentEntryPrice) return;
    
    const slValue = parseFloat(newSl);
    const entryPrice = parseFloat(currentEntryPrice);
    
    if (!isNaN(slValue) && !isNaN(entryPrice) && entryPrice > 0) {
      const percentageDiff = ((entryPrice - slValue) / entryPrice) * 100;
      
      if (!isNaN(percentageDiff)) {
        setPercentageValue(Math.round(percentageDiff));
      }
    }
  }, [newSl, currentEntryPrice, usePercentage, isEditing]);

  const handleModifySl = async () => {
    try {
      if (!newSl) {
        toast.error("Please enter a stop loss value");
        return;
      }

      const slValue = parseFloat(newSl);
      if (isNaN(slValue) || slValue <= 0) {
        toast.error("Please enter a valid stop loss value");
        return;
      }

      const encodedSymbol = encodeURIComponent(symbol).replace(/&/g, '%26');
      const response = await api.get(
        `/api/order/change_sl?symbol=${encodedSymbol}&sl=${newSl}`
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
    setPercentageValue("");
    setUsePercentage(false);
  };

  const handlePercentageChange = (e) => {
    setIsEditing(true);
    const value = e.target.value;
    // Store percentage as integer (no decimals)
    setPercentageValue(value);
    
    if (currentEntryPrice && value) {
      const percentageNum = parseInt(value, 10);
      if (!isNaN(percentageNum) && percentageNum >= 0) {
        const percentage = percentageNum / 100;
        const calculatedSL = currentEntryPrice * (1 - percentage);
        setNewSl(calculatedSL.toFixed(2));
      } else {
        setNewSl("");
      }
    }
    setIsEditing(false);
  };

  const handleAbsoluteChange = (e) => {
    setIsEditing(true);
    const value = e.target.value;
    setNewSl(value);
    
    if (usePercentage && currentEntryPrice && value) {
      const slValue = parseFloat(value);
      const entryPrice = parseFloat(currentEntryPrice);
      
      if (!isNaN(slValue) && !isNaN(entryPrice) && entryPrice > 0) {
        const percentageDiff = ((entryPrice - slValue) / entryPrice) * 100;
        
        if (!isNaN(percentageDiff)) {
          setPercentageValue(Math.round(percentageDiff));
        }
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
              Current Entry: {currentEntryPrice ? currentEntryPrice.toFixed(2) : "Not set"}
            </Typography>
            <Typography variant="body2" sx={{ color: "#f4f4f5" }}>
              Current SL: {currentSl || "Not set"}
            </Typography>
          </Box>
          
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <Typography variant="body2" sx={{ mr: 1, color: "#f4f4f5" }}>
              Stop Loss
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
              label="SL Percentage (%)"
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
                  max: 100,
                  step: 1
                }
              }}
            />
          ) : (
            <TextField
              label="Absolute Stop Loss"
              type="number"
              value={newSl}
              onChange={handleAbsoluteChange}
              variant="outlined"
              size="small"
              fullWidth
              sx={modalStyles.input}
              InputProps={{
                inputProps: { 
                  min: 0,
                  step: 0.01
                }
              }}
            />
          )}
          
          {usePercentage && newSl && (() => {
            const slValue = parseFloat(newSl);
            const percentageNum = parseInt(percentageValue, 10);
            return !isNaN(slValue) && !isNaN(percentageNum) ? (
              <Typography variant="body2" sx={{ mt: 1, color: "#f4f4f5", fontSize: "0.85rem" }}>
                Calculated SL: {newSl} ({percentageValue}%)
              </Typography>
            ) : null;
          })()}
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
            disabled={!newSl || isNaN(parseFloat(newSl)) || parseFloat(newSl) <= 0}
          >
            Modify SL
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default ModifySlModal;
