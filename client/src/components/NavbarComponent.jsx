import React, { useState, useContext } from "react";
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
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode";

export default function NavbarComponent() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const currentPath = location.pathname;
  const { token, logout } = useContext(AuthContext);

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
    window.location.href = "http://localhost:8000/api/auth";
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
