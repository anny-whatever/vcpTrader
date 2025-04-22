import { alpha } from "@mui/material/styles";

// Reusable modal styling to maintain a consistent look across all modals
export const modalStyles = {
  // Paper styles for the modal container
  paper: {
    backgroundColor: alpha("#18181b", 0.7), // Semi-transparent dark background
    backdropFilter: "blur(12px)", // Strong glass effect
    borderRadius: "16px", // Rounded corners
    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)", // Soft shadow
    border: `1px solid ${alpha("#ffffff", 0.05)}`, // Subtle border
    overflow: "hidden",
    padding: "8px",
    backgroundImage: `
      linear-gradient(120deg, ${alpha("#27272a", 0.3)} 0%, ${alpha(
      "#18181b",
      0.3
    )} 100%)
    `, // Subtle gradient
  },

  // Title styling
  title: {
    fontSize: "1.1rem",
    fontWeight: 600,
    color: "#f4f4f5", // Zinc-100
    padding: "16px 16px 8px 16px",
    borderBottom: `1px solid ${alpha("#ffffff", 0.05)}`,
  },

  // Content styling
  content: {
    padding: "16px",
  },

  // Action buttons container
  actions: {
    padding: "8px 16px 16px 16px",
    borderTop: `1px solid ${alpha("#ffffff", 0.05)}`,
    justifyContent: "flex-end",
  },

  // Primary button (confirm, submit, etc.)
  primaryButton: {
    background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)", // Indigo gradient
    color: "white",
    borderRadius: "12px",
    textTransform: "none",
    fontWeight: 600,
    padding: "8px 16px",
    transition: "transform 0.2s ease, filter 0.2s ease",
    boxShadow:
      "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "&:hover": {
      transform: "translateY(-1px)",
      filter: "brightness(110%)",
      boxShadow:
        "0 6px 10px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    },
  },

  // Secondary button (cancel, close, etc.)
  secondaryButton: {
    color: "#a1a1aa", // Zinc-400
    borderRadius: "12px",
    textTransform: "none",
    fontWeight: 500,
    padding: "8px 16px",
    "&:hover": {
      backgroundColor: alpha("#ffffff", 0.05),
    },
  },

  // Success button (buy, confirm, etc.)
  successButton: {
    background: "linear-gradient(135deg, #10b981 0%, #059669 100%)", // Emerald gradient
    color: "white",
    borderRadius: "12px",
    textTransform: "none",
    fontWeight: 600,
    padding: "8px 16px",
    transition: "transform 0.2s ease, filter 0.2s ease",
    boxShadow:
      "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "&:hover": {
      transform: "translateY(-1px)",
      filter: "brightness(110%)",
      boxShadow:
        "0 6px 10px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    },
  },

  // Danger button (sell, delete, etc.)
  dangerButton: {
    background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)", // Red gradient
    color: "white",
    borderRadius: "12px",
    textTransform: "none",
    fontWeight: 600,
    padding: "8px 16px",
    transition: "transform 0.2s ease, filter 0.2s ease",
    boxShadow:
      "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "&:hover": {
      transform: "translateY(-1px)",
      filter: "brightness(110%)",
      boxShadow:
        "0 6px 10px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    },
  },

  // Form input
  input: {
    "& .MuiInputBase-root": {
      borderRadius: "12px",
      backgroundColor: alpha("#27272a", 0.6),
      transition: "background-color 0.2s ease",
      "&:hover": {
        backgroundColor: alpha("#27272a", 0.8),
      },
      "&.Mui-focused": {
        backgroundColor: alpha("#27272a", 0.8),
        boxShadow: `0 0 0 2px ${alpha("#6366f1", 0.4)}`,
      },
    },
    "& .MuiInputLabel-root": {
      color: "#a1a1aa", // Zinc-400
      fontSize: "0.85rem",
    },
    "& .MuiInputBase-input": {
      color: "#f4f4f5", // Zinc-100
    },
    "& .MuiOutlinedInput-notchedOutline": {
      borderColor: alpha("#ffffff", 0.1),
    },
  },
};

export default modalStyles;
