import axios from "axios";

// Use environment variable if set (Vite automatically exposes variables prefixed with VITE_)
const baseURL = "http://api.devstatz.com";

const api = axios.create({
  baseURL,
});

// Request interceptor: Attach the JWT from localStorage (if it exists)
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("jwt");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Log errors for debugging (you can also integrate with an error logging service)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API response error:", error);
    return Promise.reject(error);
  }
);

export default api;
