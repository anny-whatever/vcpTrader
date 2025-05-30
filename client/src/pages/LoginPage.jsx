import React, { useState, useContext } from "react";
import {
  Avatar,
  Button,
  TextField,
  Typography,
  Container,
  Box,
  InputAdornment,
  IconButton,
  Link,
  useTheme,
  alpha,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import { motion } from "framer-motion";
import { AuthContext } from "../utils/AuthContext";
import api from "../utils/api";
import { Card, CardContent } from "../components/ui/Card";

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      duration: 0.5,
      when: "beforeChildren",
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring",
      stiffness: 300,
      damping: 24,
    },
  },
};

const logoVariants = {
  hidden: { scale: 0.8, opacity: 0 },
  visible: {
    scale: 1,
    opacity: 1,
    transition: {
      type: "spring",
      stiffness: 500,
      damping: 25,
      delay: 0.2,
    },
  },
};

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { saveToken } = useContext(AuthContext);
  const theme = useTheme();

  // Handle toggle password visibility
  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  // Handle login submission
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    // Prepare form data as x-www-form-urlencoded
    const data = new URLSearchParams();
    data.append("username", email);
    data.append("password", password);

    try {
      const response = await api.post(
        "https://api.tradekeep.in/api/login",
        data,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      // Save the JWT token using AuthContext
      saveToken(response.data.access_token);

      // Redirect to dashboard
      window.location.href = "/";
    } catch (error) {
      if (error.response) {
        setError(
          error.response.data.detail ||
            "Login failed. Please check your credentials."
        );
      } else {
        setError("Network error. Please try again.");
      }
      setLoading(false);
    }
  };

  return (
    <Box
      component={motion.div}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
        backgroundImage: `radial-gradient(circle at 25% 15%, ${alpha(
          theme.palette.primary.dark,
          0.2
        )} 0%, transparent 50%), 
                          radial-gradient(circle at 75% 75%, ${alpha(
                            theme.palette.primary.main,
                            0.1
                          )} 0%, transparent 50%)`,
      }}
    >
      <Container maxWidth="sm">
        <Card variant="glass">
          <CardContent padding="large">
            <Box sx={{ textAlign: "center", mb: 3 }}>
              <motion.div variants={logoVariants}>
                <Avatar
                  sx={{
                    mx: "auto",
                    bgcolor: "primary.main",
                    width: 64,
                    height: 64,
                    boxShadow: `0 0 20px ${alpha(
                      theme.palette.primary.main,
                      0.4
                    )}`,
                  }}
                >
                  <LockOutlinedIcon fontSize="large" />
                </Avatar>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Typography
                  component="h1"
                  variant="h4"
                  sx={{
                    mt: 2,
                    fontWeight: 700,
                    background:
                      "linear-gradient(45deg, #f5f5f5 30%, #a1a1aa 90%)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  theTerminal
                </Typography>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  Sign in to access your trading dashboard
                </Typography>
              </motion.div>
            </Box>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Box
                  sx={{
                    p: 2,
                    mb: 3,
                    borderRadius: 2,
                    bgcolor: alpha(theme.palette.error.main, 0.1),
                    border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
                  }}
                >
                  <Typography color="error.main" variant="body2">
                    {error}
                  </Typography>
                </Box>
              </motion.div>
            )}

            <Box component="form" onSubmit={handleSubmit} noValidate>
              <motion.div variants={itemVariants}>
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  id="uid"
                  label="User ID"
                  name="uid"
                  autoComplete="username"
                  autoFocus
                  value={email}
                  type="text"
                  onChange={(e) => setEmail(e.target.value)}
                  inputProps={{
                    autoCapitalize: "none",
                    autoCorrect: "off",
                  }}
                  sx={{ mb: 2 }}
                />
              </motion.div>

              <motion.div variants={itemVariants}>
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  name="password"
                  label="Password"
                  type={showPassword ? "text" : "password"}
                  id="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          aria-label="toggle password visibility"
                          onClick={handleTogglePassword}
                          edge="end"
                        >
                          {showPassword ? (
                            <VisibilityOffIcon />
                          ) : (
                            <VisibilityIcon />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  inputProps={{
                    autoCapitalize: "none",
                    autoCorrect: "off",
                  }}
                  sx={{ mb: 3 }}
                />
              </motion.div>

              <motion.div variants={itemVariants}>
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  color="primary"
                  size="large"
                  disabled={loading}
                  sx={{
                    py: 1.5,
                    fontWeight: 600,
                    boxShadow: `0 8px 16px ${alpha(
                      theme.palette.primary.main,
                      0.2
                    )}`,
                  }}
                >
                  {loading ? "Signing in..." : "Sign In"}
                </Button>
              </motion.div>

              <motion.div variants={itemVariants}>
                <Box sx={{ mt: 3, textAlign: "center" }}>
                  <Link
                    href="#"
                    variant="body2"
                    color="primary"
                    sx={{
                      opacity: 0.8,
                      "&:hover": { opacity: 1 },
                    }}
                  >
                    Forgot password?
                  </Link>
                </Box>
              </motion.div>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
};

export default LoginPage;
