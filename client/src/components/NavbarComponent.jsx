// NavbarComponent.jsx
import React, { useState, useContext, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import TickerComponent from "./TickerComponent";
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Button,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { AuthContext } from "../utils/AuthContext";
import { DataContext } from "../utils/DataContext";
import { jwtDecode } from "jwt-decode";
import api from "../utils/api"; // our configured axios instance

export default function NavbarComponent() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notificationAnchorEl, setNotificationAnchorEl] = useState(null);
  const [alertModalOpen, setAlertModalOpen] = useState(false);
  const [modalAlerts, setModalAlerts] = useState([]);
  const location = useLocation();
  const currentPath = location.pathname;
  const { token, logout } = useContext(AuthContext);
  // For the dropdown notifications (alert messages) and for the alert modal (priceAlerts)
  const { alertMessages, priceAlerts } = useContext(DataContext);

  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token);
      userRole = decoded.role || "";
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  if (currentPath === "/login") {
    return null;
  }

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const redirectToZerodhaLogin = () => {
    window.location.href = "https://api.devstatz.com/api/auth";
  };

  // Notification (dropdown) menu handlers
  const handleNotificationOpen = (event) => {
    setNotificationAnchorEl(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchorEl(null);
  };

  // Alert modal handlers
  const handleAlertModalOpen = () => {
    // Load alerts from priceAlerts (or empty array if not available)
    setModalAlerts(priceAlerts || []);
    setAlertModalOpen(true);
  };

  const handleAlertModalClose = () => {
    setAlertModalOpen(false);
  };

  // Delete an alert from the modal using our api instance with query parameters
  const handleDeleteAlert = async (alertId) => {
    try {
      await api.delete("/api/alerts/remove", { params: { alert_id: alertId } });
      setModalAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
    } catch (error) {
      if (error.response) {
        console.error("Error deleting alert:", error.response.data);
      } else {
        console.error("Error during alert deletion:", error.message);
      }
    }
  };

  const drawer = (
    <Box
      onClick={handleDrawerToggle}
      sx={{
        textAlign: "center",
        bgcolor: "#18181B",
        height: "100%",
        backdropFilter: "blur(8px)",
      }}
    >
      <Typography variant="h6" sx={{ my: 2, color: "white" }}>
        theTerminal
      </Typography>
      <List>
        <ListItem disablePadding>
          <ListItemButton component={Link} to="/" sx={{ textAlign: "center" }}>
            <ListItemText primary="Dashboard" sx={{ color: "white" }} />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton
            component={Link}
            to="/allpositions"
            sx={{ textAlign: "center" }}
          >
            <ListItemText primary="All Positions" sx={{ color: "white" }} />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton
            component={Link}
            to="/screener"
            sx={{ textAlign: "center" }}
          >
            <ListItemText primary="Screener" sx={{ color: "white" }} />
          </ListItemButton>
        </ListItem>
        {userRole === "admin" && (
          <ListItem disablePadding>
            <ListItemButton
              onClick={redirectToZerodhaLogin}
              sx={{ textAlign: "center" }}
            >
              <ListItemText primary="Zerodha Login" sx={{ color: "white" }} />
            </ListItemButton>
          </ListItem>
        )}
        {token && (
          <ListItem disablePadding>
            <ListItemButton onClick={logout} sx={{ textAlign: "center" }}>
              <ListItemText primary="Logout" sx={{ color: "white" }} />
            </ListItemButton>
          </ListItem>
        )}
      </List>
    </Box>
  );

  return (
    <>
      <AppBar
        position="static"
        sx={{
          bgcolor: "#18181B",
          backdropFilter: "blur(8px)",
          boxShadow: 3,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: "none" } }}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            theTerminal
          </Typography>
          <Box sx={{ display: { xs: "none", md: "block" } }}>
            <Button
              component={Link}
              to="/"
              sx={{
                color: "white",
                bgcolor:
                  currentPath === "/" ? "rgba(255,255,255,0.1)" : "transparent",
                mx: 1,
                borderRadius: "8px",
                textTransform: "none",
                fontWeight: "normal",
                px: 3,
                "&:hover": { bgcolor: "rgba(255,255,255,0.15)" },
              }}
            >
              Dashboard
            </Button>
            <Button
              component={Link}
              to="/allpositions"
              sx={{
                color: "white",
                bgcolor:
                  currentPath === "/allpositions"
                    ? "rgba(255,255,255,0.1)"
                    : "transparent",
                mx: 1,
                borderRadius: "8px",
                textTransform: "none",
                fontWeight: "normal",
                px: 3,
                "&:hover": { bgcolor: "rgba(255,255,255,0.15)" },
              }}
            >
              All Positions
            </Button>
            <Button
              component={Link}
              to="/screener"
              sx={{
                color: "white",
                bgcolor:
                  currentPath === "/screener"
                    ? "rgba(255,255,255,0.1)"
                    : "transparent",
                mx: 1,
                borderRadius: "8px",
                textTransform: "none",
                fontWeight: "normal",
                px: 3,
                "&:hover": { bgcolor: "rgba(255,255,255,0.15)" },
              }}
            >
              Screener
            </Button>
            {userRole === "admin" && (
              <Button
                onClick={redirectToZerodhaLogin}
                sx={{
                  color: "white",
                  mx: 1,
                  borderRadius: "8px",
                  textTransform: "none",
                  fontWeight: "normal",
                  px: 3,
                  bgcolor: "rgba(6,95,70,0.85)",
                  "&:hover": { bgcolor: "rgba(6,95,70,1)" },
                }}
              >
                Zerodha Login
              </Button>
            )}
            {token && (
              <Button
                onClick={logout}
                sx={{
                  color: "white",
                  mx: 1,
                  borderRadius: "8px",
                  textTransform: "none",
                  fontWeight: "normal",
                  px: 3,
                  bgcolor: "rgba(255,0,0,0.85)",
                  "&:hover": { bgcolor: "rgba(255,0,0,1)" },
                }}
              >
                Logout
              </Button>
            )}
          </Box>
          {/* Notification Dropdown Button (using first SVG) */}
          <IconButton
            color="inherit"
            onClick={handleNotificationOpen}
            sx={{ ml: 1 }}
            aria-controls="notification-menu"
            aria-haspopup="true"
            aria-label="notifications"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-6"
              style={{ width: "24px", height: "24px" }}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m7.875 14.25 1.214 1.942a2.25 2.25 0 0 0 1.908 1.058h2.006c.776 0 1.497-.4 1.908-1.058l1.214-1.942M2.41 9h4.636a2.25 2.25 0 0 1 1.872 1.002l.164.246a2.25 2.25 0 0 0 1.872 1.002h2.092a2.25 2.25 0 0 0 1.872-1.002l.164-.246A2.25 2.25 0 0 1 16.954 9h4.636M2.41 9a2.25 2.25 0 0 0-.16.832V12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 12V9.832c0-.287-.055-.57-.16-.832M2.41 9a2.25 2.25 0 0 1 .382-.632l3.285-3.832a2.25 2.25 0 0 1 1.708-.786h8.43c.657 0 1.281.287 1.709.786l3.284 3.832c.163.19.291.404.382.632M4.5 20.25h15A2.25 2.25 0 0 0 21.75 18v-2.625c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125V18a2.25 2.25 0 0 0 2.25 2.25Z"
              />
            </svg>
          </IconButton>
          {/* Alert Modal Button (using second SVG) */}
          <IconButton
            color="inherit"
            onClick={handleAlertModalOpen}
            sx={{ ml: 1 }}
            aria-label="view all alerts"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-6"
              style={{ width: "24px", height: "24px" }}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
              />
            </svg>
          </IconButton>
          {/* Notification Dropdown Menu */}
          <Menu
            id="notification-menu"
            anchorEl={notificationAnchorEl}
            open={Boolean(notificationAnchorEl)}
            onClose={handleNotificationClose}
            anchorOrigin={{
              vertical: "bottom",
              horizontal: "right",
            }}
            transformOrigin={{
              vertical: "top",
              horizontal: "right",
            }}
            PaperProps={{
              sx: {
                bgcolor: "#27272a", // zinc-800
                color: "white",
              },
            }}
          >
            {alertMessages && alertMessages.length > 0 ? (
              alertMessages.map((alert) => (
                <MenuItem key={alert.id} onClick={handleNotificationClose}>
                  <Typography variant="body2" noWrap>
                    {alert.message}
                  </Typography>
                </MenuItem>
              ))
            ) : (
              <MenuItem onClick={handleNotificationClose}>
                <Typography variant="body2">No notifications</Typography>
              </MenuItem>
            )}
          </Menu>
          {/* Alert Modal Dialog */}
          <Dialog
            open={alertModalOpen}
            onClose={handleAlertModalClose}
            fullWidth
            maxWidth="sm"
            PaperProps={{
              sx: { bgcolor: "#27272a", color: "white", borderRadius: "10px" },
            }}
          >
            <DialogTitle>All Alerts</DialogTitle>
            <DialogContent dividers>
              {modalAlerts && modalAlerts.length > 0 ? (
                modalAlerts.map((alert) => (
                  <Box
                    key={alert.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 1,
                      py: 0.5,
                      borderBottom: "1px solid #444",
                    }}
                  >
                    <Typography variant="body2" noWrap>
                      <strong>{alert.symbol}</strong>
                      <Chip
                        label={
                          alert.alert_type === "sl" ? "Stop Loss" : "Target"
                        }
                        size="small"
                        sx={{
                          ml: 1,
                          bgcolor:
                            alert.alert_type === "sl" ? "#ef4444" : "#22c55e",
                          color: "white",
                        }}
                      />
                      <Chip
                        label={alert.price}
                        size="small"
                        sx={{
                          ml: 1,
                          bgcolor: "#4b5563",
                          color: "white",
                        }}
                      />
                    </Typography>
                    {userRole === "admin" && (
                      <Button
                        variant="contained"
                        color="error"
                        size="small"
                        onClick={() => handleDeleteAlert(alert.id)}
                        sx={{ ml: 1 }}
                      >
                        Delete
                      </Button>
                    )}
                  </Box>
                ))
              ) : (
                <Typography variant="body2">No alerts available.</Typography>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={handleAlertModalClose} color="inherit">
                Close
              </Button>
            </DialogActions>
          </Dialog>
        </Toolbar>
      </AppBar>
      <Box component="nav">
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: 240,
              bgcolor: "#18181B",
              backdropFilter: "blur(8px)",
            },
          }}
        >
          {drawer}
        </Drawer>
      </Box>
      <TickerComponent />
    </>
  );
}
