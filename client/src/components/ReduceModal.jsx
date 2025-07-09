import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Switch,
  FormControlLabel,
} from "@mui/material";
import api from "../utils/api";
import { Toaster, toast } from "sonner";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";
import modalStyles from "./ui/ModalStyles";

function ReduceModal({ isOpen, onClose, symbol, currentQty }) {
  const [reduceQuantity, setReduceQuantity] = useState("");
  const [usePercentage, setUsePercentage] = useState(false);
  const [percentageValue, setPercentageValue] = useState("25"); // Default to 25%
  const [isEditing, setIsEditing] = useState(false);
  
  // Update quantity when percentage changes
  useEffect(() => {
    if (!isEditing && usePercentage && percentageValue && currentQty) {
      const percentageNum = parseInt(percentageValue, 10);
      if (!isNaN(percentageNum) && percentageNum > 0) {
        const percentage = percentageNum / 100;
        const calculatedQty = Math.floor(currentQty * percentage);
        setReduceQuantity(calculatedQty.toString());
      }
    }
  }, [usePercentage, percentageValue, currentQty, isEditing]);

  const sendReduceOrder = async (reduceQty) => {
    try {
      if (!reduceQty || reduceQty <= 0) {
        toast.error("Please enter a valid quantity to reduce");
        return;
      }

      if (reduceQty > currentQty) {
        toast.error("Reduce quantity cannot be greater than position quantity");
        return;
      }

      const encodedSymbol = encodeURIComponent(symbol).replace(/&/g, '%26');
      const response = await api.get(
        `/api/order/reduce?symbol=${encodedSymbol}&qty=${reduceQty}`
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
    setPercentageValue("25");
    setUsePercentage(false);
  };
  
  const handlePercentageChange = (e) => {
    setIsEditing(true);
    const value = e.target.value;
    setPercentageValue(value);
    
    if (currentQty && value) {
      const percentageNum = parseInt(value, 10);
      if (!isNaN(percentageNum) && percentageNum > 0) {
        const percentage = percentageNum / 100;
        const calculatedQty = Math.floor(currentQty * percentage);
        setReduceQuantity(calculatedQty.toString());
      } else {
        setReduceQuantity("");
      }
    }
    setIsEditing(false);
  };
  
  const handleQuantityChange = (e) => {
    setIsEditing(true);
    const value = e.target.value;
    setReduceQuantity(value);
    
    if (usePercentage && currentQty && value) {
      const qty = parseInt(value, 10);
      if (!isNaN(qty) && qty > 0) {
        const percentage = (qty / currentQty) * 100;
        if (!isNaN(percentage)) {
          setPercentageValue(Math.round(percentage).toString());
        }
      }
    }
    setIsEditing(false);
  };

  // Common percentage buttons
  const percentageButtons = [25, 50, 75, 100];

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
              Current Quantity: {currentQty}
            </Typography>
          </Box>
          
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <Typography variant="body2" sx={{ mr: 1, color: "#f4f4f5" }}>
              Quantity
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
            <>
              <TextField
                label="Percentage (%)"
                type="number"
                value={percentageValue}
                onChange={handlePercentageChange}
                variant="outlined"
                size="small"
                fullWidth
                sx={modalStyles.input}
                InputProps={{
                  inputProps: { 
                    min: 1, 
                    max: 100,
                    step: 1
                  }
                }}
              />
              
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 2 }}>
                {percentageButtons.map((percent) => (
                  <Button
                    key={percent}
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setPercentageValue(percent.toString());
                      const calculatedQty = Math.floor(currentQty * (percent / 100));
                      setReduceQuantity(calculatedQty.toString());
                    }}
                    sx={{
                      borderColor: "#27272a",
                      color: percentageValue === percent.toString() ? "#3b82f6" : "#a1a1aa",
                      borderWidth: percentageValue === percent.toString() ? 2 : 1,
                      fontSize: "0.75rem",
                      py: 0.5,
                      minWidth: 0,
                      "&:hover": {
                        borderColor: "#3b82f6",
                        bgcolor: "rgba(59, 130, 246, 0.1)",
                      },
                    }}
                  >
                    {percent}%
                  </Button>
                ))}
              </Box>
              
              {percentageValue && currentQty && (() => {
                const percentageNum = parseInt(percentageValue, 10);
                return !isNaN(percentageNum) && percentageNum > 0 ? (
                  <Typography 
                    variant="body2" 
                    sx={{ mt: 1, color: "#f4f4f5", fontSize: "0.85rem" }}
                  >
                    Calculated quantity: {Math.floor(currentQty * (percentageNum / 100))}
                  </Typography>
                ) : null;
              })()}
            </>
          ) : (
            <TextField
              label="Reduce Quantity"
              type="number"
              value={reduceQuantity}
              onChange={handleQuantityChange}
              variant="outlined"
              size="small"
              fullWidth
              inputProps={{ min: 1, max: currentQty }}
              sx={modalStyles.input}
            />
          )}
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
            disabled={!reduceQuantity || isNaN(parseInt(reduceQuantity, 10)) || parseInt(reduceQuantity, 10) <= 0}
          >
            Reduce
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default ReduceModal;
