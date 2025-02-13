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
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";

function ModifySlModal({
  isOpen,
  onClose,
  AvailableRisk,
  UsedRisk,
  symbol,
  currentEntryPrice,
}) {
  const [modifyMethodPercentage, setModifyMethodPercentage] = useState(false);
  const [sl, setSl] = useState("");
  const [slPercentage, setSlPercentage] = useState("");

  const calculateSlForPercentage = () => {
    return (
      currentEntryPrice - currentEntryPrice * (parseFloat(slPercentage) / 100)
    );
  };

  const sendModifySl = async () => {
    try {
      if (modifyMethodPercentage) {
        const slByPercentage = calculateSlForPercentage();
        const response = await api.get(
          `/api/order/change_sl?symbol=${symbol}&sl=${slByPercentage}`
        );
        PlayToastSound();
        toast.success(
          response?.data?.message ||
            "Stop-loss modified successfully (percentage)!",
          { duration: 5000 }
        );
      } else {
        const response = await api.get(
          `/api/order/change_sl?symbol=${symbol}&sl=${sl}`
        );
        PlayToastSound();
        toast.success(
          response?.data?.message || "Stop-loss modified successfully!",
          { duration: 5000 }
        );
      }
    } catch (error) {
      PlayErrorSound();
      console.error("Error modifying stop-loss:", error);
      toast.error("Error modifying stop-loss.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
    setSl("");
    setSlPercentage("");
    setModifyMethodPercentage(false);
  };

  return (
    <>
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
          Modify Stop-loss for {symbol}
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
              Absolute
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={modifyMethodPercentage}
                  onChange={(e) => setModifyMethodPercentage(e.target.checked)}
                  color="primary"
                  size="small"
                />
              }
              label="Percentage"
              sx={{
                m: 0,
                ".MuiFormControlLabel-label": { fontSize: "0.8rem" },
              }}
            />
          </Box>
          {modifyMethodPercentage ? (
            <TextField
              label="Stop-loss %"
              type="number"
              value={slPercentage}
              onChange={(e) => setSlPercentage(e.target.value)}
              variant="filled"
              size="small"
              fullWidth
              InputProps={{ disableUnderline: true }}
              sx={{
                bgcolor: "#27272A",
                borderRadius: "12px",
                width: "60%",
                "& .MuiInputBase-root": { color: "white" },
                "& .MuiInputLabel-root": { color: "white", fontSize: "0.8rem" },
              }}
            />
          ) : (
            <TextField
              label="Stop-loss"
              type="number"
              value={sl}
              onChange={(e) => setSl(e.target.value)}
              variant="filled"
              size="small"
              fullWidth
              InputProps={{ disableUnderline: true }}
              sx={{
                bgcolor: "#27272A",
                borderRadius: "12px",
                width: "60%",
                "& .MuiInputBase-root": { color: "white" },
                "& .MuiInputLabel-root": { color: "white", fontSize: "0.8rem" },
              }}
            />
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
              sendModifySl();
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
            Modify
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default ModifySlModal;
