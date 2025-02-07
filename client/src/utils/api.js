// api.js
import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

// Add a request interceptor to attach the JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jwt");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
