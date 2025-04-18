// index.jsx
import React from "react"; // default import
console.log(React);
// import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HeroUIProvider } from "@heroui/react";
import App from "./App";
import "./index.css";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";

createRoot(document.getElementById("root")).render(
  <HeroUIProvider>
    <main className="h-screen text-foreground bg-background">
      <App />
    </main>
  </HeroUIProvider>
);
