import React, { useState, useContext } from "react";
import {
  Avatar,
  Button,
  Card,
  CardContent,
  CssBaseline,
  TextField,
  Typography,
  Container,
  Box,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { AuthContext } from "../utils/AuthContext"; // Adjust the path as needed
import api from "../utils/api";

const theme = createTheme({
  palette: {
    primary: { main: "#1976d2" },
    secondary: { main: "#ff4081" },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { saveToken } = useContext(AuthContext);

  // Handle login submission by calling the /login endpoint.

  const handleSubmit = async (event) => {
    event.preventDefault();

    // Prepare form data as x-www-form-urlencoded
    const data = new URLSearchParams();
    data.append("username", email);
    data.append("password", password);

    try {
      const response = await api.post(
        "https://api.devstatz.com/api/login",
        data,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );
      // The response data is available on response.data
      const result = response.data;

      // Save the JWT token using AuthContext (and in localStorage)
      saveToken(result.access_token);

      // Redirect to your protected route (dashboard)
      window.location.href = "/";
    } catch (error) {
      // Axios errors have a response property if the request was made and the server responded
      if (error.response) {
        console.error("Login failed:", error.response.data);
      } else {
        console.error("Error during login:", error.message);
      }
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2,
        }}
      >
        <Container maxWidth="sm">
          <Card sx={{ borderRadius: 3, boxShadow: 3 }}>
            <CardContent sx={{ p: 4 }}>
              <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
                <Avatar sx={{ bgcolor: "warning.main", width: 56, height: 56 }}>
                  <LockOutlinedIcon fontSize="large" />
                </Avatar>
              </Box>
              <Typography
                component="h1"
                variant="h5"
                align="center"
                gutterBottom
              >
                Sign in to theTerminal
              </Typography>
              <Box
                component="form"
                onSubmit={handleSubmit}
                noValidate
                sx={{ mt: 1 }}
              >
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
                />
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  name="password"
                  label="Password"
                  type="password"
                  id="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  inputProps={{
                    autoCapitalize: "none",
                    autoCorrect: "off",
                  }}
                />
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  color="warning"
                  size="large"
                  sx={{ mt: 3, mb: 2, borderRadius: 2 }}
                >
                  Sign In
                </Button>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  Forgot password? Irresponsible bitch, call me
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Container>
      </Box>
    </ThemeProvider>
  );
};

export default LoginPage;
