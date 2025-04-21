// main.jsx
import React, { Suspense } from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";
import { ThemeProvider, CssBaseline } from "@mui/material";
import theme from "./utils/theme.js";
import "@fontsource/inter/300.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";

// Loading component for suspense fallback
const LoadingFallback = () => (
  <div className="h-screen w-screen flex items-center justify-center bg-zinc-900">
    <div className="animate-pulse text-indigo-500 text-xl font-semibold">
      Loading...
    </div>
  </div>
);

// Create the root and render the app
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Suspense fallback={<LoadingFallback />}>
        <App />
      </Suspense>
    </ThemeProvider>
  </React.StrictMode>
);
