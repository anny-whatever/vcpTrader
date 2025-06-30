import React, { useState, useEffect, useContext } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  Menu,
  MenuItem,
  Avatar,
  Tooltip,
  ButtonBase,
  useMediaQuery,
  styled,
  alpha,
  Button,
  Switch,
  FormControlLabel,
} from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import MenuIcon from "@mui/icons-material/Menu";
import DashboardIcon from "@mui/icons-material/Dashboard";
import BarChartIcon from "@mui/icons-material/BarChart";
import SearchIcon from "@mui/icons-material/Search";
import ListAltIcon from "@mui/icons-material/ListAlt";
import NotificationsIcon from "@mui/icons-material/Notifications";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import CloseIcon from "@mui/icons-material/Close";
import LogoutIcon from "@mui/icons-material/Logout";
import { useTheme } from "@mui/material/styles";
import api from "../../utils/api";
import { toast } from "sonner";
import { PlayToastSound, PlayErrorSound } from "../../utils/PlaySound";
import { AuthContext } from "../../utils/AuthContext";

// Styled components
const StyledAppBar = styled(AppBar)(({ theme }) => ({
  backgroundColor: alpha(theme.palette.background.default, 0.7),
  backdropFilter: "blur(10px)",
  boxShadow: "none",
  borderBottom: `1px solid ${alpha(theme.palette.divider, 0.05)}`,
  transition: "all 0.3s ease",
}));

const StyledToolbar = styled(Toolbar)(({ theme }) => ({
  height: 70,
  display: "flex",
  justifyContent: "space-between",
  padding: theme.spacing(0, 2),
  [theme.breakpoints.up("sm")]: {
    padding: theme.spacing(0, 3),
  },
}));

const BrandBox = styled(Box)(({ theme }) => ({
  display: "flex",
  alignItems: "center",
  justifyContent: "flex-start",
  "& .brand-text": {
    background: "linear-gradient(45deg, #f5f5f5 30%, #a1a1aa 90%)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    fontWeight: 800,
    letterSpacing: "-0.025em",
  },
}));

const LogoWrapper = styled(Box)(({ theme }) => ({
  position: "relative",
  width: 32,
  height: 32,
  marginRight: theme.spacing(1.5),
  borderRadius: "50%",
  background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  boxShadow: "0 0 10px 2px rgba(99, 102, 241, 0.3)",
  overflow: "hidden",
  "&::after": {
    content: '""',
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background:
      "linear-gradient(45deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0) 70%)",
    borderRadius: "50%",
  },
}));

const NavAction = styled(ButtonBase)(({ theme, active }) => ({
  borderRadius: 8,
  padding: theme.spacing(1, 1.5),
  transition: "all 0.2s ease",
  backgroundColor: active
    ? alpha(theme.palette.primary.main, 0.1)
    : "transparent",
  color: active ? theme.palette.primary.main : theme.palette.text.primary,
  fontWeight: active ? 600 : 500,
  fontSize: "0.875rem",
  "&:hover": {
    backgroundColor: active
      ? alpha(theme.palette.primary.main, 0.15)
      : alpha(theme.palette.action.hover, 0.05),
  },
}));

const MobileDrawer = styled(Drawer)(({ theme }) => ({
  "& .MuiDrawer-paper": {
    width: 280,
    backgroundColor: alpha(theme.palette.background.default, 0.95),
    backdropFilter: "blur(10px)",
    boxShadow: theme.shadows[8],
    padding: theme.spacing(2, 0),
  },
}));

const DrawerHeader = styled(Box)(({ theme }) => ({
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: theme.spacing(0, 2),
  marginBottom: theme.spacing(2),
}));

const NavItem = styled(ListItemButton)(({ theme, active }) => ({
  borderRadius: theme.spacing(1),
  marginBottom: theme.spacing(0.5),
  marginLeft: theme.spacing(1),
  marginRight: theme.spacing(1),
  padding: theme.spacing(1, 2),
  color: active ? theme.palette.primary.main : theme.palette.text.primary,
  backgroundColor: active
    ? alpha(theme.palette.primary.main, 0.1)
    : "transparent",
  "&:hover": {
    backgroundColor: active
      ? alpha(theme.palette.primary.main, 0.15)
      : alpha(theme.palette.action.hover, 0.05),
  },
  "& .MuiListItemIcon-root": {
    color: active ? theme.palette.primary.main : theme.palette.text.secondary,
    minWidth: "40px",
  },
  "& .MuiListItemText-primary": {
    fontWeight: active ? 600 : 500,
    fontSize: "0.875rem",
  },
}));

const AccountMenu = styled(Menu)(({ theme }) => ({
  "& .MuiPaper-root": {
    borderRadius: 12,
    minWidth: 180,
    backgroundColor: alpha(theme.palette.background.paper, 0.9),
    backdropFilter: "blur(10px)",
    boxShadow:
      "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    marginTop: theme.spacing(1.5),
    "& .MuiList-root": {
      padding: theme.spacing(1),
    },
    "& .MuiMenuItem-root": {
      padding: theme.spacing(1, 2),
      borderRadius: theme.spacing(1),
      margin: theme.spacing(0.5, 0),
      "&:hover": {
        backgroundColor: alpha(theme.palette.action.hover, 0.1),
      },
    },
  },
}));

// Nav item animation variants
const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      type: "spring",
      stiffness: 300,
      damping: 24,
    },
  },
  exit: { opacity: 0, x: -20, transition: { duration: 0.2 } },
};

// Logo animation variants
const logoVariants = {
  hidden: { scale: 0.8, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      stiffness: 500,
      damping: 25,
    },
  },
};

// Router links animation
const linkVariants = {
  hover: {
    y: -2,
    transition: {
      type: "spring",
      stiffness: 400,
      damping: 10,
    },
  },
};

const Navbar = ({
  onLogout,
  userName = "User",
  userRole = "user",
  notificationCount = 0,
  alertMessages = [],
}) => {
  const { multiplierEnabled, toggleMultiplier } = useContext(AuthContext);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const location = useLocation();
  const currentPath = location.pathname;

  // Debug log for role verification
  React.useEffect(() => {
    console.log('Navbar userRole:', userRole);
  }, [userRole]);

  // State for mobile drawer
  const [mobileOpen, setMobileOpen] = useState(false);

  // State for the notification menu
  const [notificationsAnchorEl, setNotificationsAnchorEl] = useState(null);
  const notificationsOpen = Boolean(notificationsAnchorEl);

  // State for the account menu
  const [accountAnchorEl, setAccountAnchorEl] = useState(null);
  const accountOpen = Boolean(accountAnchorEl);

  // Toggle mobile drawer
  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  // Handle notification menu
  const handleNotificationsOpen = (event) => {
    setNotificationsAnchorEl(event.currentTarget);
  };

  const handleNotificationsClose = () => {
    setNotificationsAnchorEl(null);
  };

  // Handle account menu
  const handleAccountOpen = (event) => {
    setAccountAnchorEl(event.currentTarget);
  };

  const handleAccountClose = () => {
    setAccountAnchorEl(null);
  };

  // Handle logout
  const handleLogout = () => {
    handleAccountClose();
    onLogout();
  };

  // Navigation items
  const navItems = [
    {
      name: "Dashboard",
      path: "/",
      icon: <DashboardIcon />,
    },
    {
      name: "All Positions",
      path: "/allpositions",
      icon: <BarChartIcon />,
    },
    {
      name: "Screener",
      path: "/screener",
      icon: <SearchIcon />,
    },
    {
      name: "Watchlist",
      path: "/watchlist",
      icon: <ListAltIcon />,
    },
    {
      name: "Alerts",
      path: "/alerts",
      icon: <NotificationsActiveIcon />,
    },
  ];

  // Admin actions
  const adminActions = [
    {
      name: "Zerodha Login",
      path: "https://api.tradekeep.in/api/auth",
      external: true,
    },
  ];

  // Clear all notifications
  const handleClearAllNotifications = async () => {
    try {
      await api.delete("/api/alerts/messages/clear");
      PlayToastSound();
      toast.success("All notifications cleared", {
        duration: 5000,
      });
      // Close the menu
      handleNotificationsClose();
    } catch (error) {
      PlayErrorSound();
      toast.error("Failed to clear notifications", {
        duration: 5000,
      });
      console.error("Error clearing notifications:", error);
    }
  };

  // Mobile drawer content
  const drawer = (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <DrawerHeader>
        <BrandBox>
          <LogoWrapper
            component={motion.div}
            variants={logoVariants}
            initial="hidden"
            animate="visible"
          >
            <Typography variant="h5" sx={{ color: "white", fontWeight: 700 }}>
              T
            </Typography>
          </LogoWrapper>
          <Typography variant="h6" className="brand-text">
            theTerminal
          </Typography>
        </BrandBox>
        <IconButton onClick={handleDrawerToggle}>
          <CloseIcon />
        </IconButton>
      </DrawerHeader>

      <List component="nav" sx={{ flexGrow: 1 }}>
        <AnimatePresence>
          {navItems.map((item, index) => (
            <motion.div
              key={item.name}
              variants={itemVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              custom={index}
            >
              <NavItem
                component={Link}
                to={item.path}
                active={currentPath === item.path ? 1 : 0}
                onClick={handleDrawerToggle}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.name} />
              </NavItem>
            </motion.div>
          ))}

          {userRole === "admin" &&
            adminActions.map((action, index) => (
              <motion.div
                key={action.name}
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                custom={index + navItems.length}
              >
                <NavItem
                  component={action.external ? "a" : Link}
                  to={!action.external ? action.path : undefined}
                  href={action.external ? action.path : undefined}
                  active={0}
                  onClick={handleDrawerToggle}
                >
                  <ListItemText primary={action.name} />
                </NavItem>
              </motion.div>
            ))}
        </AnimatePresence>
      </List>

      <Box sx={{ p: 2, mt: "auto" }}>
        <ListItem disablePadding>
          <NavItem onClick={handleLogout}>
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="Logout" />
          </NavItem>
        </ListItem>
      </Box>
    </Box>
  );

  return (
    <>
      <StyledAppBar position="sticky">
        <StyledToolbar>
          {/* Brand and logo */}
          <BrandBox>
            {isMobile && (
              <IconButton
                edge="start"
                color="inherit"
                aria-label="menu"
                onClick={handleDrawerToggle}
                sx={{ mr: 1 }}
              >
                <MenuIcon />
              </IconButton>
            )}
            <LogoWrapper
              component={motion.div}
              variants={logoVariants}
              initial="hidden"
              animate="visible"
            >
              <Typography variant="h5" sx={{ color: "white", fontWeight: 700 }}>
                T
              </Typography>
            </LogoWrapper>
            <Typography variant="h6" className="brand-text">
              theTerminal
            </Typography>
          </BrandBox>

          {/* Desktop Navigation */}
          {!isMobile && (
            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
              {navItems.map((item) => (
                <motion.div
                  key={item.name}
                  variants={linkVariants}
                  whileHover="hover"
                >
                  <NavAction
                    component={Link}
                    to={item.path}
                    active={currentPath === item.path ? 1 : 0}
                  >
                    {item.name}
                  </NavAction>
                </motion.div>
              ))}
            </Box>
          )}

          {/* Right side actions */}
          <Box sx={{ display: "flex", alignItems: "center" }}>
            {/* Notifications */}
            <Tooltip title="Notifications">
              <IconButton
                color="inherit"
                onClick={handleNotificationsOpen}
                size="medium"
                sx={{ mr: 1 }}
              >
                <Badge badgeContent={alertMessages?.length || 0} color="error">
                  <NotificationsIcon />
                </Badge>
              </IconButton>
            </Tooltip>

            {/* Account */}
            <Box
              onClick={handleAccountOpen}
              sx={{
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
                borderRadius: 1,
                py: 0.5,
                px: 1,
                "&:hover": {
                  bgcolor: "action.hover",
                },
              }}
            >
              <Avatar
                sx={{
                  width: 32,
                  height: 32,
                  bgcolor: "primary.main",
                  fontSize: "0.875rem",
                  boxShadow: "0 0 0 2px rgba(255, 255, 255, 0.1)",
                }}
              >
                {userName?.charAt(0).toUpperCase() || "U"}
              </Avatar>

              {!isMobile && (
                <>
                  <Box
                    sx={{
                      ml: 1,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-start",
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {userName || "User"}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ textTransform: "capitalize" }}
                    >
                      {userRole || "user"}
                    </Typography>
                  </Box>
                  <KeyboardArrowDownIcon
                    fontSize="small"
                    sx={{ ml: 0.5, color: "text.secondary" }}
                  />
                </>
              )}
            </Box>
          </Box>
        </StyledToolbar>
      </StyledAppBar>

      {/* Mobile Drawer */}
      <MobileDrawer
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
      >
        {drawer}
      </MobileDrawer>

      {/* Notifications Menu */}
      <Menu
        anchorEl={notificationsAnchorEl}
        open={notificationsOpen}
        onClose={handleNotificationsClose}
        PaperProps={{
          sx: {
            mt: 1.5,
            ml: { xs: 0, sm: -2 },
            width: 360,
            maxWidth: "100%",
            maxHeight: "70vh",
            borderRadius: 2,
            bgcolor: alpha(theme.palette.background.paper, 0.9),
            backdropFilter: "blur(10px)",
            boxShadow:
              "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
          },
        }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
      >
        <Box
          sx={{
            p: 2,
            borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="subtitle1" fontWeight={600}>
            Notifications
          </Typography>
          {alertMessages?.length > 0 && (
            <Typography
              variant="body2"
              color="primary"
              sx={{ cursor: "pointer" }}
              onClick={handleClearAllNotifications}
            >
              Clear all
            </Typography>
          )}
        </Box>

        {!alertMessages || alertMessages.length === 0 ? (
          <Box sx={{ p: 4, textAlign: "center" }}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                margin: "0 auto 16px",
                color: theme.palette.text.secondary,
              }}
            >
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            <Typography variant="body1" fontWeight={500} color="text.primary">
              No notifications yet
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              We'll let you know when something arrives
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              maxHeight: "50vh",
              overflow: "auto",
              py: 1,
              "&::-webkit-scrollbar": {
                width: "4px",
              },
              "&::-webkit-scrollbar-track": {
                background: "transparent",
              },
              "&::-webkit-scrollbar-thumb": {
                background: alpha(theme.palette.primary.main, 0.2),
                borderRadius: "10px",
              },
              "&::-webkit-scrollbar-thumb:hover": {
                background: alpha(theme.palette.primary.main, 0.4),
              },
            }}
          >
            {/* Real alert notifications */}
            {alertMessages.map((alert) => (
              <MenuItem
                key={`notification-${alert.id}`}
                onClick={handleNotificationsClose}
                sx={{
                  px: 2,
                  py: 1.5,
                  borderRadius: 1,
                  mx: 1,
                  my: 0.5,
                  "&:hover": {
                    backgroundColor: alpha(theme.palette.action.hover, 0.1),
                  },
                }}
              >
                <Box sx={{ width: "100%" }}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mb: 0.5,
                      alignItems: "center",
                    }}
                  >
                    <Typography variant="body2" fontWeight={600}>
                      {alert.symbol}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        "& svg": { mr: 0.5 },
                      }}
                    >
                      {alert.alert_type === "sl" ? "Stop Loss" : "Target"}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Triggered at ₹{alert.triggered_price}
                  </Typography>
                </Box>
              </MenuItem>
            ))}

            {/* Add View All Alerts link */}
            <Box
              sx={{
                p: 2,
                borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                display: "flex",
                justifyContent: "center",
              }}
            >
              <Button
                component={Link}
                to="/alerts"
                startIcon={<NotificationsActiveIcon />}
                onClick={handleNotificationsClose}
                variant="outlined"
                size="small"
                sx={{
                  borderRadius: 1,
                  px: 2,
                  py: 0.75,
                  fontSize: "0.75rem",
                }}
              >
                View All Alerts
              </Button>
            </Box>
          </Box>
        )}
      </Menu>

      {/* Account Menu */}
      <AccountMenu
        anchorEl={accountAnchorEl}
        open={accountOpen}
        onClose={handleAccountClose}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
      >
        <MenuItem onClick={handleAccountClose}>
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <AccountCircleIcon sx={{ mr: 1.5 }} />
            <Typography variant="body2">Profile</Typography>
          </Box>
        </MenuItem>

        {userRole === "admin" && [
          <MenuItem
            key="zerodha-login"
            component="a"
            href="https://api.tradekeep.in/api/auth"
            onClick={handleAccountClose}
          >
            <Typography variant="body2">Zerodha Login</Typography>
          </MenuItem>,
          
          <MenuItem key="multiplier-toggle" onClick={(e) => e.stopPropagation()}>
            <FormControlLabel
              control={
                <Switch
                  checked={multiplierEnabled}
                  onChange={toggleMultiplier}
                  size="small"
                />
              }
              label={
                <Typography variant="body2">
                  Multiplier
                </Typography>
              }
              sx={{ margin: 0 }}
            />
          </MenuItem>
        ]}

        {/* Only show Zerodha login for admin users, no multiplier toggle for observers */}
        {userRole === "observer" && (
          <MenuItem onClick={handleAccountClose}>
            <Typography variant="body2" sx={{ color: "#a1a1aa" }}>
              Observer Mode
            </Typography>
          </MenuItem>
        )}

        <MenuItem onClick={handleLogout}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              color: theme.palette.error.main,
            }}
          >
            <LogoutIcon sx={{ mr: 1.5 }} />
            <Typography variant="body2">Logout</Typography>
          </Box>
        </MenuItem>
      </AccountMenu>
    </>
  );
};

export default Navbar;
