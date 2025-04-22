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
import { PlayErrorSound } from "../utils/PlaySound";
import modalStyles from "./ui/ModalStyles";

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

      toast.success(
        response?.data?.message || "Watchlist added successfully!",
        { duration: 5000 }
      );
    } catch (error) {
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
          ...modalStyles.paper,
          // Positioning to the bottom right corner
          position: "fixed",
          bottom: 16,
          right: 16,
          m: 0,
        },
      }}
    >
      <DialogTitle sx={modalStyles.title}>Add New Watchlist</DialogTitle>
      <DialogContent sx={modalStyles.content}>
        <TextField
          label="Watchlist Name"
          type="text"
          value={watchlistName}
          onChange={(e) => setWatchlistName(e.target.value)}
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
        <Button onClick={handleAddWatchlist} sx={modalStyles.primaryButton}>
          Add
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default AddWatchlistModal;
