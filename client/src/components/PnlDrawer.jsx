// PnlDrawer.jsx
import React, { useState, useContext, useEffect } from "react";
import { DataContext } from "../utils/DataContext";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode";

const PnlDrawer = () => {
  const { positions, liveData } = useContext(DataContext);
  const { token } = useContext(AuthContext);
  const [isOpen, setIsOpen] = useState(true);
  const [totalPnl, setTotalPnl] = useState(0);
  const [capitalUsed, setCapitalUsed] = useState(0);
  const [multiplier, setMultiplier] = useState(1);

  // Determine multiplier based on user role
  useEffect(() => {
    if (token) {
      try {
        const decoded = jwtDecode(token);
        if (decoded.role && decoded.role !== "admin") {
          setMultiplier(25);
        }
      } catch (error) {
        console.error("Failed to decode token:", error);
      }
    }
  }, [token]);

  // Merge liveData into positions just like in AllPositions
  useEffect(() => {
    if (positions && liveData) {
      positions.forEach((pos) => {
        const liveItem = liveData.find(
          (item) => item.instrument_token === pos.token
        );
        if (liveItem) {
          pos.last_price = liveItem.last_price;
        }
      });
    }
  }, [positions, liveData]);

  // Compute total P&L and capital used based on updated positions
  useEffect(() => {
    if (positions) {
      let runningPnl = 0;
      let runningCap = 0;
      positions.forEach((pos) => {
        runningPnl +=
          (pos.last_price - pos.entry_price) * pos.current_qty + pos.booked_pnl;
        runningCap += pos.entry_price * pos.current_qty;
      });
      setTotalPnl(runningPnl);
      setCapitalUsed(runningCap);
    }
  }, [positions, liveData]);

  return (
    <div
      className={`fixed bottom-4 right-4 bg-zinc-800 text-white rounded-lg shadow-lg transition-all duration-300 ${
        isOpen ? "w-64 p-4" : "w-12 p-2"
      }`}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full text-center focus:outline-none"
      >
        {isOpen ? "Hide" : "P&L"}
      </button>
      {isOpen && (
        <div className="mt-2">
          <div className="text-sm text-zinc-400">Total P&L</div>
          <div
            className={`text-xl mt-1 ${
              totalPnl >= 0 ? "text-green-400" : "text-red-400"
            }`}
          >
            {(totalPnl * multiplier).toFixed(2)}
            <span className="ml-2 text-sm text-zinc-400">
              (
              {capitalUsed === 0
                ? "0.00"
                : ((totalPnl / capitalUsed) * 100).toFixed(2)}
              %)
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default PnlDrawer;
