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

function ModifyTgtModal({
  isOpen,
  onClose,
  AvailableRisk,
  UsedRisk,
  symbol,
  currentEntryPrice,
}) {
  const [modifyMethodPercentage, setModifyMethodPercentage] = useState(false);
  const [tgtPercentage, setTgtPercentage] = useState("");
  const [tgt, setTgt] = useState("");

  const calculateTgtForPercentage = () => {
    return (
      currentEntryPrice + currentEntryPrice * (parseFloat(tgtPercentage) / 100)
    );
  };

  const sendModifyTgt = async () => {
    try {
      if (modifyMethodPercentage) {
        const tgtByPercentage = calculateTgtForPercentage();
        const response = await api.get(
          `/api/order/change_tgt?symbol=${symbol}&tgt=${tgtByPercentage}`
        );
        PlayToastSound();
        toast.success(
          response?.data?.message ||
            "Target modified successfully (percentage)!",
          { duration: 5000 }
        );
      } else {
        const response = await api.get(
          `/api/order/change_tgt?symbol=${symbol}&tgt=${tgt}`
        );
        PlayToastSound();
        toast.success(
          response?.data?.message || "Target modified successfully!",
          { duration: 5000 }
        );
      }
    } catch (error) {
      PlayErrorSound();
      console.error("Error modifying target:", error);
      toast.error("Error modifying target.", { duration: 5000 });
    }
  };

  const handleClose = () => {
    onClose();
    setTgt("");
    setTgtPercentage("");
    setModifyMethodPercentage(false);
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
          Modify Target for {symbol}
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
              label="Target %"
              type="number"
              value={tgtPercentage}
              onChange={(e) => setTgtPercentage(e.target.value)}
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
              label="Target"
              type="number"
              value={tgt}
              onChange={(e) => setTgt(e.target.value)}
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
              sendModifyTgt();
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

export default ModifyTgtModal;
