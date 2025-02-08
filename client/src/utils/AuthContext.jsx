import React, { createContext, useState, useEffect, useCallback } from "react";

export const AuthContext = createContext({
  token: null,
  saveToken: () => {},
  logout: () => {},
});

export const AuthProvider = ({ children }) => {
  // Initialize token state from localStorage
  const [token, setToken] = useState(() => localStorage.getItem("jwt") || null);

  // Function to save the token to state and localStorage
  const saveToken = useCallback((newToken) => {
    localStorage.setItem("jwt", newToken);
    setToken(newToken);
  }, []);

  // Function to logout the user
  const logout = useCallback(() => {
    localStorage.removeItem("jwt");
    setToken(null);
  }, []);

  // Listen for changes to the JWT in localStorage (e.g. from another tab)
  useEffect(() => {
    const handleStorageChange = (event) => {
      if (event.key === "jwt") {
        setToken(event.newValue);
      }
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  return (
    <AuthContext.Provider value={{ token, saveToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
