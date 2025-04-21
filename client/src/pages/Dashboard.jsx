import React, { useContext, useEffect, useState, useMemo } from "react";
import { DataContext } from "../utils/DataContext";
import { AuthContext } from "../utils/AuthContext";
import { Grid, Box, Typography, useMediaQuery, Button } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  Table,
  TableHeader,
  TableBody,
  TableColumn,
  TableRow,
  TableCell,
  Spinner,
  Item,
} from "../utils/compat";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
} from "recharts";
import { jwtDecode } from "jwt-decode"; // Note: if jwt-decode is CommonJS, see previous answer

// --- Helper Functions ---

// Avoid calling .toFixed on undefined or NaN
function safeNumber(val) {
  return typeof val === "number" && !isNaN(val) ? val : 0;
}

// Format date string as dd/mm/yy
function formatDate(dateString) {
  if (!dateString) return "";
  const d = new Date(dateString);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yy = String(d.getFullYear()).slice(-2);
  return `${dd}/${mm}/${yy}`;
}

// Convert a date string into a numeric timestamp for sorting
function getTimestamp(dateStr) {
  if (!dateStr) return 0;
  return new Date(dateStr).getTime();
}

/**
 * Compute aggregate statistics from an array of trades.
 * Returns an object with total PnL, drawdown, accuracy, risk/reward, etc.,
 * and additionally calculates the average profit percentage and average loss percentage.
 */
function computeTradeStats(trades, multiplier) {
  const totalPnLAll = trades.reduce(
    (acc, t) => acc + safeNumber(t.final_pnl),
    0
  );

  let runningTotal = 0;
  let peak = 0;
  let drawdownLocal = 0;
  trades.forEach((t) => {
    runningTotal += safeNumber(t.final_pnl);
    if (runningTotal > peak) peak = runningTotal;
    const dd = peak - runningTotal;
    if (dd > drawdownLocal) drawdownLocal = dd;
  });

  let maxCapital = 0;
  trades.forEach((t) => {
    const cap = safeNumber(t.entry_price) * safeNumber(t.highest_qty);
    if (cap > maxCapital) maxCapital = cap;
  });

  const totalTrades = trades.length;
  const wins = trades.filter((t) => safeNumber(t.final_pnl) > 0).length;
  const accuracyLocal = totalTrades ? wins / totalTrades : 0;

  const winningPnls = trades
    .filter((t) => safeNumber(t.final_pnl) > 0)
    .map((t) => safeNumber(t.final_pnl));
  const losingPnls = trades
    .filter((t) => safeNumber(t.final_pnl) < 0)
    .map((t) => Math.abs(safeNumber(t.final_pnl)));

  const sumWins = winningPnls.reduce((a, b) => a + b, 0);
  const sumLosses = losingPnls.reduce((a, b) => a + b, 0);

  const avgWin = winningPnls.length > 0 ? sumWins / winningPnls.length : 0;
  const avgLossAbs = losingPnls.length > 0 ? sumLosses / losingPnls.length : 1;

  const rr = avgWin / avgLossAbs || 0;
  const avgProfitLocal = avgWin;
  const avgLossLocal = avgLossAbs;
  const avgPnlLocal = totalTrades ? totalPnLAll / totalTrades : 0;
  const profitFactorLocal =
    sumLosses === 0 ? Number.POSITIVE_INFINITY : sumWins / sumLosses;

  // Calculate average profit percentage and average loss percentage.
  // For each trade, calculate the percent change as ((exit - entry) / entry) * 100.
  const profitPercents = trades
    .filter(
      (t) =>
        safeNumber(t.entry_price) !== 0 &&
        (safeNumber(t.exit_price) - safeNumber(t.entry_price)) /
          safeNumber(t.entry_price) >
          0
    )
    .map(
      (t) =>
        ((safeNumber(t.exit_price) - safeNumber(t.entry_price)) /
          safeNumber(t.entry_price)) *
        100
    );
  const lossPercents = trades
    .filter(
      (t) =>
        safeNumber(t.entry_price) !== 0 &&
        (safeNumber(t.exit_price) - safeNumber(t.entry_price)) /
          safeNumber(t.entry_price) <
          0
    )
    .map(
      (t) =>
        ((safeNumber(t.exit_price) - safeNumber(t.entry_price)) /
          safeNumber(t.entry_price)) *
        100
    );
  const avgProfitPercent =
    profitPercents.length > 0
      ? profitPercents.reduce((a, b) => a + b, 0) / profitPercents.length
      : 0;
  const avgLossPercent =
    lossPercents.length > 0
      ? Math.abs(lossPercents.reduce((a, b) => a + b, 0) / lossPercents.length)
      : 0;

  return {
    histTotalPnl: totalPnLAll * multiplier,
    maxDrawdown: drawdownLocal * multiplier,
    highestCapitalUsed: maxCapital * multiplier,
    accuracy: accuracyLocal,
    riskReward: rr,
    avgProfit: avgProfitLocal * multiplier,
    avgLoss: avgLossLocal * multiplier,
    avgPnl: avgPnlLocal * multiplier,
    profitFactor: profitFactorLocal * multiplier,
    avgProfitPercent, // in percent (%)
    avgLossPercent, // in percent (%)
  };
}

/**
 * Prepare chart data (line and bar charts) from trades.
 * Returns an object with properties `lineChartData` and `barChartData`.
 */
function prepareChartData(trades, multiplier) {
  if (!trades || trades.length === 0) {
    return { lineChartData: [], barChartData: [] };
  }

  // Sort trades ascending by exit_time (earliest first)
  const ascendingTrades = [...trades].sort(
    (a, b) => getTimestamp(a.exit_time) - getTimestamp(b.exit_time)
  );

  let cumulative = 0;
  const lineChartData = ascendingTrades.map((t, idx) => {
    const finalPnl = safeNumber(t.final_pnl);
    cumulative += finalPnl;
    return {
      name: formatDate(t.exit_time) || `T${idx + 1}`,
      trailingPnl: parseInt(cumulative * multiplier),
    };
  });

  // Compute bar chart data: percent difference ignoring quantity
  const barChartData = ascendingTrades.map((t, idx) => {
    const entryP = safeNumber(t.entry_price);
    const exitP = safeNumber(t.exit_price);
    const diffPercent = entryP === 0 ? 0 : ((exitP - entryP) / entryP) * 100;
    return {
      name: formatDate(t.exit_time) || `T${idx + 1}`,
      percentPnl: parseFloat(diffPercent.toFixed(2)),
    };
  });

  return { lineChartData, barChartData };
}

/**
 * Paginate and sort the trades for display in the table.
 * Returns an object with the current page of trades and total number of pages.
 */
function paginateTrades(trades, page, pageSize) {
  const sortedTrades = trades
    .slice()
    .sort((a, b) => getTimestamp(b.exit_time) - getTimestamp(a.exit_time));
  const totalPages = Math.ceil(sortedTrades.length / pageSize);
  const startIndex = page * pageSize;
  const currentTrades = sortedTrades.slice(startIndex, startIndex + pageSize);
  return { currentTrades, totalPages };
}

// --- Dashboard Component ---

function Dashboard() {
  const { historicalTrades } = useContext(DataContext);
  const { token, logout } = useContext(AuthContext);

  // States for stats, chart data, and paginated trades
  const [stats, setStats] = useState({
    histTotalPnl: 0,
    maxDrawdown: 0,
    highestCapitalUsed: 0,
    accuracy: 0,
    riskReward: 0,
    avgProfit: 0,
    avgLoss: 0,
    avgPnl: 0,
    profitFactor: 0,
    avgProfitPercent: 0,
    avgLossPercent: 0,
  });
  const [lineChartData, setLineChartData] = useState([]);
  const [barChartData, setBarChartData] = useState([]);
  const [currentTrades, setCurrentTrades] = useState([]);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  let multiplier = 1;
  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token);
      userRole = decoded.role || "";
      if (userRole !== "admin") {
        multiplier = 25;
      }
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // Only run stats computation when historicalTrades data is available
  useEffect(() => {
    if (historicalTrades && historicalTrades.length > 0) {
      const computedStats = computeTradeStats(historicalTrades, multiplier);
      setStats(computedStats);
    }
  }, [historicalTrades, multiplier]);

  // Only prepare chart data when historicalTrades data is available
  useEffect(() => {
    if (historicalTrades && historicalTrades.length > 0) {
      const { lineChartData, barChartData } = prepareChartData(
        historicalTrades,
        multiplier
      );
      setLineChartData(lineChartData);
      setBarChartData(barChartData);
    } else {
      setLineChartData([]);
      setBarChartData([]);
    }
  }, [historicalTrades, multiplier]);

  // Only paginate trades when historicalTrades data is available
  useEffect(() => {
    if (historicalTrades && historicalTrades.length > 0) {
      const { currentTrades, totalPages } = paginateTrades(
        historicalTrades,
        page,
        pageSize
      );
      setCurrentTrades(currentTrades);
      setTotalPages(totalPages);
    }
  }, [historicalTrades, page, pageSize]);

  // Derived display values
  const displayedHistTotalPnl = stats.histTotalPnl.toFixed(2);
  const displayedMaxDD = stats.maxDrawdown.toFixed(2);
  const displayedHighCap = stats.highestCapitalUsed.toFixed(2);
  const displayedAccuracy = (stats.accuracy * 100).toFixed(2);
  const displayedRR = stats.riskReward.toFixed(2);
  const displayedAvgProfit = stats.avgProfit.toFixed(2);
  const displayedAvgLoss = stats.avgLoss.toFixed(2);
  const displayedAvgPnl = stats.avgPnl.toFixed(2);
  const displayedPF = Number.isFinite(stats.profitFactor)
    ? stats.profitFactor.toFixed(2)
    : "∞";
  const displayedAvgProfitPercent = stats.avgProfitPercent.toFixed(2);
  const displayedAvgLossPercent = stats.avgLossPercent.toFixed(2);

  return (
    <Box sx={{ color: "white", px: isMobile ? 2 : 4, py: 3 }}>
      {/* HISTORICAL TRADES STATS ROW */}
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 3,
          mb: 3,
          justifyContent: { xs: "center", md: "flex-start" },
        }}
      >
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Hist. Total P&L
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: stats.histTotalPnl >= 0 ? "#22c55e" : "#ef4444",
              fontSize: "1rem",
            }}
          >
            {displayedHistTotalPnl}
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Max DD
          </Typography>
          <Typography
            variant="body1"
            sx={{ color: "#ef4444", fontSize: "1rem" }}
          >
            {displayedMaxDD}
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Highest Cap
          </Typography>
          <Typography variant="body1" sx={{ fontSize: "1rem" }}>
            {displayedHighCap}
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Accuracy
          </Typography>
          <Typography
            variant="body1"
            sx={{ color: "#22c55e", fontSize: "1rem" }}
          >
            {displayedAccuracy}%
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            R:R
          </Typography>
          <Typography variant="body1" sx={{ fontSize: "1rem" }}>
            {displayedRR}
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Avg Profit
          </Typography>
          <Typography
            variant="body1"
            sx={{ color: "#22c55e", fontSize: "1rem" }}
          >
            {displayedAvgProfit}
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Avg Loss
          </Typography>
          <Typography
            variant="body1"
            sx={{ color: "#ef4444", fontSize: "1rem" }}
          >
            {displayedAvgLoss}
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Avg PnL
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: stats.avgPnl >= 0 ? "#22c55e" : "#ef4444",
              fontSize: "1rem",
            }}
          >
            {displayedAvgPnl}
          </Typography>
        </Box>
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Profit Factor
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: stats.profitFactor >= 1 ? "#22c55e" : "#ef4444",
              fontSize: "1rem",
            }}
          >
            {displayedPF}
          </Typography>
        </Box>
        {/* New: Average Profit % */}
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Avg Profit %
          </Typography>
          <Typography
            variant="body1"
            sx={{ color: "#22c55e", fontSize: "1rem" }}
          >
            {displayedAvgProfitPercent}%
          </Typography>
        </Box>
        {/* New: Average Loss % */}
        <Box
          sx={{ display: "flex", flexDirection: "column", minWidth: "100px" }}
        >
          <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
            Avg Loss %
          </Typography>
          <Typography
            variant="body1"
            sx={{ color: "#ef4444", fontSize: "1rem" }}
          >
            {displayedAvgLossPercent}%
          </Typography>
        </Box>
      </Box>

      {/* MIDDLE SECTION: 2 CHARTS (Line + Bar) */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {/* LEFT: LINE CHART for trailing PnL */}
        <Grid item xs={12} md={6}>
          <Box
            sx={{
              backgroundColor: "#18181B",
              borderRadius: "1rem",
              height: isMobile ? "200px" : "300px",
              boxShadow:
                "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
              p: 3,
              border: "1px solid rgba(63, 63, 70, 0.5)",
              backdropFilter: "blur(10px)",
              transition: "all 0.3s ease",
              "&:hover": {
                boxShadow:
                  "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
              },
            }}
          >
            <Typography
              variant="subtitle1"
              sx={{
                color: "#d4d4d8",
                mb: 1.5,
                fontWeight: 600,
                fontSize: "1rem",
              }}
            >
              Cumulative PnL Curve
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <LineChart
                data={lineChartData}
                margin={{ top: 10, right: 10, bottom: 30, left: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#3f3f46"
                  opacity={0.4}
                />
                <XAxis
                  dataKey="name"
                  stroke="#a1a1aa"
                  tick={{ fontSize: 12, fill: "#a1a1aa" }}
                />
                <YAxis
                  stroke="#a1a1aa"
                  tick={{ fontSize: 12, fill: "#a1a1aa" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#27272a",
                    border: "none",
                    borderRadius: "0.5rem",
                    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                  }}
                  labelStyle={{
                    color: "#e4e4e7",
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: "0.25rem",
                  }}
                  itemStyle={{ color: "#e4e4e7", fontSize: 12 }}
                />
                <Line
                  type="monotone"
                  dataKey="trailingPnl"
                  stroke="#22c55e"
                  strokeWidth={2.5}
                  dot={{ r: 3, strokeWidth: 2, fill: "#18181b" }}
                  activeDot={{ r: 6, strokeWidth: 0, fill: "#22c55e" }}
                  name="trailingPnl"
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        </Grid>

        {/* RIGHT: BAR CHART for % difference ignoring qty */}
        <Grid item xs={12} md={6}>
          <Box
            sx={{
              backgroundColor: "#18181B",
              borderRadius: "1rem",
              height: isMobile ? "200px" : "300px",
              boxShadow:
                "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
              p: 3,
              border: "1px solid rgba(63, 63, 70, 0.5)",
              backdropFilter: "blur(10px)",
              transition: "all 0.3s ease",
              "&:hover": {
                boxShadow:
                  "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
              },
            }}
          >
            <Typography
              variant="subtitle1"
              sx={{
                color: "#d4d4d8",
                mb: 1.5,
                fontWeight: 600,
                fontSize: "1rem",
              }}
            >
              % Based PnL (Ignoring Qty)
            </Typography>
            <ResponsiveContainer width="100%" height="90%">
              <BarChart
                data={barChartData}
                margin={{ top: 10, right: 10, bottom: 30, left: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#3f3f46"
                  opacity={0.4}
                />
                <XAxis
                  dataKey="name"
                  stroke="#a1a1aa"
                  tick={{ fontSize: 12, fill: "#a1a1aa" }}
                />
                <YAxis
                  stroke="#a1a1aa"
                  tick={{ fontSize: 12, fill: "#a1a1aa" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#27272a",
                    border: "none",
                    borderRadius: "0.5rem",
                    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                  }}
                  labelStyle={{
                    color: "#e4e4e7",
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: "0.25rem",
                  }}
                  itemStyle={{ color: "#e4e4e7", fontSize: 12 }}
                />
                <ReferenceLine y={0} stroke="#a1a1aa" strokeDasharray="3 3" />
                <Bar dataKey="percentPnl" name="percentPnl">
                  {barChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={
                        Number(entry.percentPnl) >= 0 ? "#22c55e" : "#ef4444"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Grid>
      </Grid>

      {/* BOTTOM AREA: Paginated Table of Historical Trades */}
      {/* DESKTOP TABLE */}
      <Box
        sx={{
          backgroundColor: "rgba(50, 50, 51, 0.5)",
          borderRadius: "1rem",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.3)",
          border: "1px solid rgba(63, 63, 70, 0.5)",
          mb: 3,
          display: { xs: "none", md: "block" },
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            p: 2,
            borderBottom: "1px solid rgba(63, 63, 70, 0.5)",
          }}
        >
          <Typography
            variant="subtitle1"
            sx={{
              color: "#d4d4d8",
              fontWeight: 600,
              fontSize: "1rem",
            }}
          >
            Historical Trades
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: "#a1a1aa",
              fontWeight: 500,
            }}
          >
            Count:{" "}
            <span style={{ color: "#f4f4f5" }}>{currentTrades.length}</span>
          </Typography>
        </Box>
        {!historicalTrades ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <Spinner size="lg" />
          </Box>
        ) : (
          <table className="w-full">
            <thead className="bg-zinc-800 border-b border-zinc-700/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Stock
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Entry Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Entry Price
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Exit Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Exit Price
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Final PnL
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                  Highest Qty
                </th>
              </tr>
            </thead>
            <tbody>
              {currentTrades.map((row, index) => {
                const stock = row.stock_name || "";
                const entryPrice = safeNumber(row.entry_price);
                const exitPrice = safeNumber(row.exit_price);
                const finalPnl = safeNumber(row.final_pnl);
                const highestQty = safeNumber(row.highest_qty);
                const entryDate = formatDate(row.entry_time);
                const exitDate = formatDate(row.exit_time);
                const isPositive = finalPnl >= 0;
                const pnlValue = (finalPnl * multiplier).toFixed(2);
                const pnlPercent = (
                  ((exitPrice - entryPrice) / entryPrice) *
                  100
                ).toFixed(1);

                return (
                  <tr
                    key={`trade-${index}-${row.trade_id || row.stock_name}`}
                    className="border-b border-zinc-800 hover:bg-zinc-900/50"
                  >
                    <td className="px-4 py-3 text-white font-medium">
                      {stock}
                    </td>
                    <td className="px-4 py-3 text-white">{entryDate}</td>
                    <td className="px-4 py-3 text-white">
                      {entryPrice.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-white">{exitDate}</td>
                    <td className="px-4 py-3 text-white">
                      {exitPrice.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 rounded text-${
                          isPositive ? "green" : "red"
                        }-500 bg-${isPositive ? "green" : "red"}-500/20`}
                      >
                        {isPositive ? "" : "-"}
                        {pnlValue.replace("-", "")} ({pnlPercent}%)
                      </span>
                    </td>
                    <td className="px-4 py-3 text-white">
                      {(highestQty * multiplier).toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Box>

      {/* MOBILE CARD LAYOUT */}
      <Box
        sx={{
          display: { xs: "block", md: "none" },
          backgroundColor: "rgba(24, 24, 27, 0.5)",
          backdropFilter: "blur(10px)",
          borderRadius: "1rem",
          boxShadow:
            "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
          p: 3,
          border: "1px solid rgba(63, 63, 70, 0.5)",
          mb: 3,
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Typography
            variant="subtitle1"
            sx={{
              color: "#d4d4d8",
              fontWeight: 600,
              fontSize: "1rem",
            }}
          >
            Historical Trades
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: "#a1a1aa",
              fontWeight: 500,
            }}
          >
            Count:{" "}
            <span style={{ color: "#f4f4f5" }}>{currentTrades.length}</span>
          </Typography>
        </Box>
        {!historicalTrades ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <Spinner size="lg" />
          </Box>
        ) : (
          <Box className="space-y-4 mt-4">
            {currentTrades.map((row, index) => {
              const stock = row.stock_name || "";
              const entryPrice = safeNumber(row.entry_price);
              const exitPrice = safeNumber(row.exit_price);
              const finalPnl = safeNumber(row.final_pnl);
              const highestQty = safeNumber(row.highest_qty);
              const entryDate = formatDate(row.entry_time);
              const exitDate = formatDate(row.exit_time);
              const isPositive = finalPnl >= 0;
              const colorClass = isPositive ? "text-green-500" : "text-red-500";
              const pnlPercentage = (
                ((exitPrice - entryPrice) / entryPrice) *
                100
              ).toFixed(1);

              return (
                <Box
                  key={`mobile-trade-${index}-${
                    row.trade_id || row.stock_name
                  }`}
                  className="flex flex-col gap-3 p-5 bg-zinc-900/80 backdrop-blur-sm rounded-xl border border-zinc-800/70 shadow-md transition-all hover:border-zinc-700 hover:bg-zinc-800/80"
                >
                  <Box className="flex items-center justify-between">
                    <Typography className="text-base font-bold text-white">
                      {stock}
                    </Typography>
                    <Box
                      className={`px-3 py-1 rounded-full ${
                        isPositive ? "bg-green-500/10" : "bg-red-500/10"
                      }`}
                    >
                      <Typography
                        className={`text-base font-semibold ${colorClass}`}
                      >
                        {(finalPnl * multiplier).toFixed(2)} ({pnlPercentage}%)
                      </Typography>
                    </Box>
                  </Box>
                  <Box className="grid grid-cols-2 gap-4 mt-2">
                    <Box className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
                      <Typography className="text-xs text-zinc-400 font-medium mb-1">
                        Entry Date
                      </Typography>
                      <Typography className="text-sm font-medium text-white">
                        {entryDate}
                      </Typography>
                    </Box>
                    <Box className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
                      <Typography className="text-xs text-zinc-400 font-medium mb-1">
                        Exit Date
                      </Typography>
                      <Typography className="text-sm font-medium text-white">
                        {exitDate}
                      </Typography>
                    </Box>
                    <Box className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
                      <Typography className="text-xs text-zinc-400 font-medium mb-1">
                        Entry Price
                      </Typography>
                      <Typography className="text-sm font-medium text-white">
                        {entryPrice.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
                      <Typography className="text-xs text-zinc-400 font-medium mb-1">
                        Exit Price
                      </Typography>
                      <Typography className="text-sm font-medium text-white">
                        {exitPrice.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
                      <Typography className="text-xs text-zinc-400 font-medium mb-1">
                        Highest Qty
                      </Typography>
                      <Typography className="text-sm font-medium text-white">
                        {(highestQty * multiplier).toFixed(2)}
                      </Typography>
                    </Box>
                    <Box className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
                      <Typography className="text-xs text-zinc-400 font-medium mb-1">
                        Final PnL
                      </Typography>
                      <Typography
                        className={`text-sm font-semibold ${colorClass}`}
                      >
                        {(finalPnl * multiplier).toFixed(2)}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              );
            })}
          </Box>
        )}
      </Box>

      {/* Pagination Controls */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          mt: 2,
          gap: 2,
          pb: 4,
        }}
      >
        <Button
          variant="flat"
          size="sm"
          className="bg-zinc-800/50 backdrop-blur-sm hover:bg-zinc-700/70 text-white px-4 min-w-[90px] h-9 border border-zinc-700/50"
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
          startContent={
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-4 h-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 19.5 8.25 12l7.5-7.5"
              />
            </svg>
          }
        >
          Previous
        </Button>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            px: 3,
            py: 1,
            backgroundColor: "rgba(24, 24, 27, 0.6)",
            backdropFilter: "blur(10px)",
            borderRadius: "0.5rem",
            border: "1px solid rgba(63, 63, 70, 0.5)",
          }}
        >
          <Typography
            variant="body2"
            sx={{
              color: "#d4d4d8",
              fontWeight: 500,
            }}
          >
            Page {page + 1} of {totalPages}
          </Typography>
        </Box>
        <Button
          variant="flat"
          size="sm"
          className="bg-zinc-800/50 backdrop-blur-sm hover:bg-zinc-700/70 text-white px-4 min-w-[90px] h-9 border border-zinc-700/50"
          disabled={page + 1 >= totalPages}
          onClick={() => setPage((p) => p + 1)}
          endContent={
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-4 h-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m8.25 4.5 7.5 7.5-7.5 7.5"
              />
            </svg>
          }
        >
          Next
        </Button>
      </Box>
    </Box>
  );
}

export default Dashboard;
