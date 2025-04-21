import { createTheme } from "@mui/material/styles";
import { alpha } from "@mui/material/styles";

// Custom theme with modern styling
const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#6366f1", // Indigo color
      light: "#818cf8",
      dark: "#4f46e5",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#10b981", // Emerald color
      light: "#34d399",
      dark: "#059669",
      contrastText: "#ffffff",
    },
    success: {
      main: "#10b981", // Emerald
      light: "#34d399",
      dark: "#059669",
    },
    error: {
      main: "#ef4444", // Red
      light: "#f87171",
      dark: "#dc2626",
    },
    warning: {
      main: "#f59e0b", // Amber
      light: "#fbbf24",
      dark: "#d97706",
    },
    info: {
      main: "#3b82f6", // Blue
      light: "#60a5fa",
      dark: "#2563eb",
    },
    background: {
      default: "#18181b", // Zinc-900
      paper: "#27272a", // Zinc-800
    },
    text: {
      primary: "#f4f4f5", // Zinc-100
      secondary: "#a1a1aa", // Zinc-400
      disabled: "#71717a", // Zinc-500
    },
    divider: "rgba(255, 255, 255, 0.12)",
    action: {
      active: "rgba(255, 255, 255, 0.56)",
      hover: "rgba(255, 255, 255, 0.08)",
      hoverOpacity: 0.08,
      selected: "rgba(255, 255, 255, 0.16)",
      selectedOpacity: 0.16,
      disabled: "rgba(255, 255, 255, 0.3)",
      disabledBackground: "rgba(255, 255, 255, 0.12)",
      disabledOpacity: 0.38,
      focus: "rgba(255, 255, 255, 0.12)",
      focusOpacity: 0.12,
      activatedOpacity: 0.24,
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      letterSpacing: "-0.025em",
    },
    h2: {
      fontWeight: 700,
      letterSpacing: "-0.025em",
    },
    h3: {
      fontWeight: 600,
      letterSpacing: "-0.025em",
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
    button: {
      fontWeight: 600,
      textTransform: "none",
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          backdropFilter: "blur(8px)",
          backgroundColor: alpha("#18181b", 0.85),
          boxShadow:
            "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: "none",
          fontWeight: 600,
          padding: "8px 16px",
          boxShadow: "none",
          "&:hover": {
            boxShadow:
              "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
            transform: "translateY(-1px)",
            transition: "all 0.2s ease-in-out",
          },
        },
        containedPrimary: {
          background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
        },
        containedSecondary: {
          background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        },
        containedSuccess: {
          background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
        },
        containedError: {
          background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
        },
        containedWarning: {
          background: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
        },
        outlinedPrimary: {
          borderWidth: 2,
        },
        outlinedSecondary: {
          borderWidth: 2,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          backdropFilter: "blur(8px)",
          backgroundColor: alpha("#27272a", 0.85),
          transition: "transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out",
          "&:hover": {
            boxShadow:
              "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
        elevation1: {
          boxShadow:
            "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        },
        elevation2: {
          boxShadow:
            "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        },
        elevation3: {
          boxShadow:
            "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        },
        elevation4: {
          boxShadow:
            "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          "& .MuiOutlinedInput-root": {
            borderRadius: 8,
            transition:
              "border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out",
            "&.Mui-focused": {
              boxShadow: `0 0 0 3px ${alpha("#6366f1", 0.25)}`,
            },
          },
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          borderRadius: 4,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: 8,
          backgroundColor: alpha("#27272a", 0.95),
          backdropFilter: "blur(8px)",
          boxShadow:
            "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
          padding: "8px 12px",
          fontSize: "0.75rem",
        },
      },
    },
    MuiTable: {
      styleOverrides: {
        root: {
          borderCollapse: "separate",
          borderSpacing: "0 4px",
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: "none",
        },
        head: {
          color: "#a1a1aa",
          fontSize: "0.75rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 600,
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          backgroundColor: alpha("#27272a", 0.5),
          "&:hover": {
            backgroundColor: alpha("#27272a", 0.8),
          },
          "& > :first-of-type": {
            borderTopLeftRadius: 8,
            borderBottomLeftRadius: 8,
          },
          "& > :last-child": {
            borderTopRightRadius: 8,
            borderBottomRightRadius: 8,
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundImage: "none",
          backgroundColor: alpha("#18181b", 0.95),
          backdropFilter: "blur(8px)",
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 16,
          backgroundImage: "none",
          backgroundColor: alpha("#27272a", 0.95),
          backdropFilter: "blur(10px)",
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontSize: "1.25rem",
          fontWeight: 600,
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          height: 3,
          borderRadius: 1.5,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 500,
          minWidth: "auto",
          "&.Mui-selected": {
            fontWeight: 600,
          },
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        "*": {
          boxSizing: "border-box",
        },
        html: {
          MozOsxFontSmoothing: "grayscale",
          WebkitFontSmoothing: "antialiased",
          height: "100%",
          width: "100%",
        },
        body: {
          height: "100%",
          width: "100%",
          backgroundSize: "cover",
          backgroundAttachment: "fixed",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          backgroundImage:
            "radial-gradient(ellipse at 40% 0%, #353535 0%, transparent 75%), radial-gradient(ellipse at 60% 0%, #4f46e5 0%, transparent 75%)",
        },
        "#root": {
          height: "100%",
          width: "100%",
        },
        ".fade-enter": {
          opacity: 0,
        },
        ".fade-enter-active": {
          opacity: 1,
          transition: "opacity 300ms ease-in",
        },
        ".fade-exit": {
          opacity: 1,
        },
        ".fade-exit-active": {
          opacity: 0,
          transition: "opacity 300ms ease-out",
        },
      },
    },
  },
  transitions: {
    easing: {
      easeInOut: "cubic-bezier(0.4, 0, 0.2, 1)",
      easeOut: "cubic-bezier(0.0, 0, 0.2, 1)",
      easeIn: "cubic-bezier(0.4, 0, 1, 1)",
      sharp: "cubic-bezier(0.4, 0, 0.6, 1)",
    },
    duration: {
      shortest: 150,
      shorter: 200,
      short: 250,
      standard: 300,
      complex: 375,
      enteringScreen: 225,
      leavingScreen: 195,
    },
  },
});

export default theme;
