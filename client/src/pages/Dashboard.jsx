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
} from "@heroui/react";
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
              borderRadius: 3,
              height: isMobile ? "200px" : "300px",
              boxShadow: 3,
              p: 2,
            }}
          >
            <Typography variant="body2" sx={{ color: "#a1a1aa", mb: 1 }}>
              Cumulative PnL Curve
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={lineChartData}
                margin={{ top: 10, right: 10, bottom: 20, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#666" />
                <XAxis
                  dataKey="name"
                  stroke="#999"
                  tick={{ fontSize: 12, fill: "#999" }}
                />
                <YAxis stroke="#999" tick={{ fontSize: 12, fill: "#999" }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#333", border: "none" }}
                  labelStyle={{ color: "#fff", fontSize: 12 }}
                  itemStyle={{ color: "#fff", fontSize: 12 }}
                />
                <Legend
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{
                    fontSize: "0.8rem",
                    color: "#999",
                    marginTop: 10,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="trailingPnl"
                  stroke="#82ca9d"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
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
              borderRadius: 3,
              height: isMobile ? "200px" : "300px",
              boxShadow: 3,
              p: 2,
            }}
          >
            <Typography variant="body2" sx={{ color: "#a1a1aa", mb: 1 }}>
              % Based PnL (Ignoring Qty)
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={barChartData}
                margin={{ top: 10, right: 10, bottom: 20, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#666" />
                <XAxis
                  dataKey="name"
                  stroke="#999"
                  tick={{ fontSize: 12, fill: "#999" }}
                />
                <YAxis stroke="#999" tick={{ fontSize: 12, fill: "#999" }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#333", border: "none" }}
                  labelStyle={{ color: "#fff", fontSize: 12 }}
                  itemStyle={{ color: "#fff", fontSize: 12 }}
                />
                <Legend
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{
                    fontSize: "0.8rem",
                    color: "#999",
                    marginTop: 10,
                  }}
                />
                <ReferenceLine y={0} stroke="#fff" strokeDasharray="3 3" />
                <Bar dataKey="percentPnl">
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
      <Typography variant="body1" sx={{ mb: 1 }}>
        Latest Trades
      </Typography>
      {!historicalTrades ? (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            mt: 4,
          }}
        >
          <Spinner size="lg" />
          <Typography variant="body2" sx={{ mt: 1 }}>
            Loading...
          </Typography>
        </Box>
      ) : (
        <>
          {/* DESKTOP TABLE */}
          <Box className="hidden md:block">
            <Table
              aria-label="Latest Historical Trades Table"
              className="m-auto rounded-md no-scrollbar bg-zinc-900"
              align="center"
            >
              <TableHeader>
                <TableColumn>Stock</TableColumn>
                <TableColumn>Entry Date</TableColumn>
                <TableColumn>Entry Price</TableColumn>
                <TableColumn>Exit Date</TableColumn>
                <TableColumn>Exit Price</TableColumn>
                <TableColumn>Final PnL</TableColumn>
                <TableColumn>Highest Qty</TableColumn>
              </TableHeader>
              <TableBody>
                {currentTrades.map((row) => {
                  const stock = row.stock_name || "";
                  const entryPrice = safeNumber(row.entry_price);
                  const exitPrice = safeNumber(row.exit_price);
                  const finalPnl = safeNumber(row.final_pnl);
                  const highestQty = safeNumber(row.highest_qty);
                  const entryDate = formatDate(row.entry_time);
                  const exitDate = formatDate(row.exit_time);
                  const isPositive = finalPnl >= 0;

                  return (
                    <TableRow
                      key={row.trade_id || row.stock_name}
                      className="hover:bg-zinc-800"
                    >
                      <TableCell>{stock}</TableCell>
                      <TableCell>{entryDate}</TableCell>
                      <TableCell>{entryPrice.toFixed(2)}</TableCell>
                      <TableCell>{exitDate}</TableCell>
                      <TableCell>{exitPrice.toFixed(2)}</TableCell>
                      <TableCell
                        className={
                          isPositive ? "text-green-500" : "text-red-500"
                        }
                      >
                        {(finalPnl * multiplier).toFixed(2)} (
                        {(
                          ((exitPrice - entryPrice) / entryPrice) *
                          100
                        ).toFixed(1)}
                        %)
                      </TableCell>
                      <TableCell>
                        {(highestQty * multiplier).toFixed(2)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Box>

          {/* MOBILE CARD LAYOUT */}
          <Box className="block mt-3 space-y-3 md:hidden">
            {currentTrades.map((row) => {
              const stock = row.stock_name || "";
              const entryPrice = safeNumber(row.entry_price);
              const exitPrice = safeNumber(row.exit_price);
              const finalPnl = safeNumber(row.final_pnl);
              const highestQty = safeNumber(row.highest_qty);
              const entryDate = formatDate(row.entry_time);
              const exitDate = formatDate(row.exit_time);
              const isPositive = finalPnl >= 0;

              return (
                <Box
                  key={row.trade_id || row.stock_name}
                  sx={{ backgroundColor: "#1e1e1e", borderRadius: 1, p: 2 }}
                >
                  <Typography variant="body2" fontWeight="bold">
                    {stock}
                  </Typography>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mt: 1,
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
                      Entry Date:
                    </Typography>
                    <Typography variant="caption">{entryDate}</Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mt: 0.5,
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
                      Entry Price:
                    </Typography>
                    <Typography variant="caption">
                      {entryPrice.toFixed(2)}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mt: 0.5,
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
                      Exit Date:
                    </Typography>
                    <Typography variant="caption">{exitDate}</Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mt: 0.5,
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
                      Exit Price:
                    </Typography>
                    <Typography variant="caption">
                      {exitPrice.toFixed(2)}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mt: 0.5,
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
                      Final PnL:
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{ color: isPositive ? "#22c55e" : "#ef4444" }}
                    >
                      {(finalPnl * multiplier).toFixed(2)} (
                      {(((exitPrice - entryPrice) / entryPrice) * 100).toFixed(
                        1
                      )}
                      %)
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mt: 0.5,
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#a1a1aa" }}>
                      Highest Qty:
                    </Typography>
                    <Typography variant="caption">
                      {(highestQty * multiplier).toFixed(2)}
                    </Typography>
                  </Box>
                </Box>
              );
            })}
          </Box>

          {/* PAGINATION CONTROLS */}
          <Box
            sx={{ display: "flex", justifyContent: "center", mt: 2, gap: 2 }}
          >
            <Button
              variant="outlined"
              size="small"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Typography variant="body2" sx={{ alignSelf: "center" }}>
              Page {page + 1} of {totalPages}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
}

export default Dashboard;
