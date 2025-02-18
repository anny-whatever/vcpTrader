// src/components/AddWatchlistModal.jsx
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
import { toast } from "sonner";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";

function AddWatchlistModal({ isOpen, onClose }) {
  const [watchlistName, setWatchlistName] = useState("");

  const handleAddWatchlist = async () => {
    if (!watchlistName.trim()) {
      toast.error("Please enter a watchlist name.");
      return;
    }
    try {
      const response = await api.post("/api/watchlist/watchlistname/add", {
        name: watchlistName,
      });
      PlayToastSound();
      toast.success(
        response?.data?.message || "Watchlist added successfully!",
        { duration: 5000 }
      );
    } catch (error) {
      console.error("Error adding watchlist:", error);
      PlayErrorSound();
      toast.error(
        (error?.response && error?.response?.data?.message) ||
          "Failed to add watchlist",
        { duration: 5000 }
      );
    }
    setWatchlistName("");
    onClose();
  };

  const handleClose = () => {
    setWatchlistName("");
    onClose();
  };

  return (
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
          // Positioning to the bottom right corner
          position: "fixed",
          bottom: 16,
          right: 16,
          m: 0,
        },
      }}
    >
      <DialogTitle sx={{ fontSize: "1rem", pb: 0.5 }}>
        Add New Watchlist
      </DialogTitle>
      <DialogContent sx={{ pb: 0.5 }}>
        <TextField
          label="Watchlist Name"
          type="text"
          value={watchlistName}
          onChange={(e) => setWatchlistName(e.target.value)}
          variant="filled"
          size="small"
          fullWidth
          InputProps={{ disableUnderline: true }}
          sx={{
            bgcolor: "#27272A",
            borderRadius: "12px",
            "& .MuiInputBase-root": { color: "white" },
            "& .MuiInputLabel-root": {
              color: "white",
              fontSize: "0.8rem",
            },
          }}
        />
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
          onClick={handleAddWatchlist}
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
          Add
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default AddWatchlistModal;
