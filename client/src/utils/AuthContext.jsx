// AuthContext.jsx
import React, { createContext, useState, useEffect, useCallback } from "react";

export const AuthContext = createContext({
  token: null,
  saveToken: () => {},
  logout: () => {},
  multiplierEnabled: true,
  toggleMultiplier: () => {},
});

export const AuthProvider = ({ children }) => {
  // Helper function to decode a JWT token and return its payload
  const decodeJWT = (token) => {
    try {
      // Split the token into its parts (header, payload, signature)
      const base64Url = token.split(".")[1];
      if (!base64Url) return null;
      // Replace URL-safe characters and decode the base64 string
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join("")
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error("Failed to decode JWT:", error);
      return null;
    }
  };

  // Function to retrieve the token from localStorage and check if it has expired.
  const getInitialToken = () => {
    const savedToken = localStorage.getItem("jwt");
    if (!savedToken) return null;
    const payload = decodeJWT(savedToken);
    // If the token has an expiration time and it's in the past, remove it.
    if (payload && payload.exp * 1000 < Date.now()) {
      localStorage.removeItem("jwt");
      return null;
    }
    return savedToken;
  };

  // Initialize token state from localStorage using the helper above.
  const [token, setToken] = useState(getInitialToken);

  // Initialize multiplier state from localStorage with default true (enabled)
  const [multiplierEnabled, setMultiplierEnabled] = useState(() => {
    const saved = localStorage.getItem("multiplierEnabled");
    return saved !== null ? JSON.parse(saved) : true;
  });

  // Function to save the token to state and localStorage.
  const saveToken = useCallback((newToken) => {
    localStorage.setItem("jwt", newToken);
    setToken(newToken);
  }, []);

  // Function to logout the user by removing the token.
  const logout = useCallback(() => {
    localStorage.removeItem("jwt");
    setToken(null);
  }, []);

  // Function to toggle multiplier setting
  const toggleMultiplier = useCallback(() => {
    setMultiplierEnabled(prev => {
      const newValue = !prev;
      localStorage.setItem("multiplierEnabled", JSON.stringify(newValue));
      return newValue;
    });
  }, []);

  // Whenever the token changes, check if it's expired and log out if needed.
  useEffect(() => {
    if (token) {
      const payload = decodeJWT(token);
      if (payload && payload.exp * 1000 < Date.now()) {
        logout();
      }
    }
  }, [token, logout]);

  // Listen for changes to the JWT in localStorage (for example, if updated in another tab).
  useEffect(() => {
    const handleStorageChange = (event) => {
      if (event.key === "jwt") {
        setToken(event.newValue);
      } else if (event.key === "multiplierEnabled") {
        setMultiplierEnabled(event.newValue ? JSON.parse(event.newValue) : true);
      }
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  return (
    <AuthContext.Provider value={{ token, saveToken, logout, multiplierEnabled, toggleMultiplier }}>
      {children}
    </AuthContext.Provider>
  );
};
