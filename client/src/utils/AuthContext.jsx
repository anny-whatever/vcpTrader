import { createContext, useState } from "react";

export const AuthContext = createContext();

/**
 * AuthProvider loads the token synchronously from localStorage so that
 * ProtectedRoute sees it on the very first render.
 */
export const AuthProvider = ({ children }) => {
  // Initialize token state from localStorage immediately
  const [token, setToken] = useState(() => localStorage.getItem("jwt") || null);

  const saveToken = (newToken) => {
    localStorage.setItem("jwt", newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem("jwt");
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, saveToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
