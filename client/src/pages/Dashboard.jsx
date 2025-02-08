import React, { useContext, useEffect, useState } from "react";
import { DataContext } from "../utils/DataContext";
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

// 1) IMPORT Recharts components for both line + bar charts
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
} from "recharts";

// Helper to avoid calling .toFixed on undefined or NaN
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

// Convert dateStr to numeric for sorting
function getTimestamp(dateStr) {
  if (!dateStr) return 0;
  return new Date(dateStr).getTime();
}

function Dashboard() {
  const { historicalTrades } = useContext(DataContext);

  // HISTORICAL TRADE STATS (like totalPnL, maxDrawdown, etc.)
  const [histTotalPnl, setHistTotalPnl] = useState(0);
  const [maxDrawdown, setMaxDrawdown] = useState(0);
  const [highestCapitalUsed, setHighestCapitalUsed] = useState(0);
  const [accuracy, setAccuracy] = useState(0);
  const [riskReward, setRiskReward] = useState(0);
  const [avgProfit, setAvgProfit] = useState(0);
  const [avgLoss, setAvgLoss] = useState(0);
  const [avgPnl, setAvgPnl] = useState(0);
  const [profitFactor, setProfitFactor] = useState(0); // Replacing expectancy

  // We'll store chart data
  const [lineChartData, setLineChartData] = useState([]); // for trailing PnL line
  const [barChartData, setBarChartData] = useState([]); // for percent-based bar

  // Pagination states for table
  const [page, setPage] = useState(0);
  const pageSize = 10; // show 10 trades per page

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  // ---------- Compute Stats ----------
  useEffect(() => {
    if (!historicalTrades || historicalTrades.length === 0) return;
    const trades = historicalTrades;

    // totalPnL
    const totalPnLAll = trades.reduce(
      (acc, t) => acc + safeNumber(t.final_pnl),
      0
    );

    // max drawdown
    let runningTotal = 0;
    let peak = 0;
    let drawdownLocal = 0;
    trades.forEach((t) => {
      runningTotal += safeNumber(t.final_pnl);
      if (runningTotal > peak) peak = runningTotal;
      const dd = peak - runningTotal;
      if (dd > drawdownLocal) drawdownLocal = dd;
    });

    // highest capital used
    let maxCapital = 0;
    trades.forEach((t) => {
      const cap = safeNumber(t.entry_price) * safeNumber(t.highest_qty);
      if (cap > maxCapital) maxCapital = cap;
    });

    // accuracy
    const totalTrades = trades.length;
    const wins = trades.filter((t) => safeNumber(t.final_pnl) > 0).length;
    const losses = trades.filter((t) => safeNumber(t.final_pnl) < 0).length;
    const accuracyLocal = totalTrades ? wins / totalTrades : 0;

    // R:R
    const winningPnls = trades
      .filter((t) => safeNumber(t.final_pnl) > 0)
      .map((t) => safeNumber(t.final_pnl));
    const losingPnls = trades
      .filter((t) => safeNumber(t.final_pnl) < 0)
      .map((t) => Math.abs(safeNumber(t.final_pnl)));

    const sumWins = winningPnls.reduce((a, b) => a + b, 0);
    const sumLosses = losingPnls.reduce((a, b) => a + b, 0);

    const avgWin = winningPnls.length > 0 ? sumWins / winningPnls.length : 0;
    const avgLossAbs =
      losingPnls.length > 0 ? sumLosses / losingPnls.length : 1;

    const rr = avgWin / avgLossAbs || 0;

    // avg profit (among winners)
    const avgProfitLocal = avgWin;
    // avg loss (among losers)
    const avgLossLocal = avgLossAbs;

    // avg PnL (all trades)
    const avgPnlLocal = totalTrades ? totalPnLAll / totalTrades : 0;

    // profit factor = sumWins / sumLosses
    const profitFactorLocal =
      sumLosses === 0 ? Number.POSITIVE_INFINITY : sumWins / sumLosses;

    setHistTotalPnl(totalPnLAll);
    setMaxDrawdown(drawdownLocal);
    setHighestCapitalUsed(maxCapital);
    setAccuracy(accuracyLocal);
    setRiskReward(rr);
    setAvgProfit(avgProfitLocal);
    setAvgLoss(avgLossLocal);
    setAvgPnl(avgPnlLocal);
    setProfitFactor(profitFactorLocal);
  }, [historicalTrades]);

  // ---------- Prepare Chart Data ----------
  useEffect(() => {
    if (!historicalTrades || historicalTrades.length === 0) {
      setLineChartData([]);
      setBarChartData([]);
      return;
    }
    // Sort ascending by exit_time => earliest exit first
    const ascendingTrades = [...historicalTrades].sort(
      (a, b) => getTimestamp(a.exit_time) - getTimestamp(b.exit_time)
    );

    // lineChartData: cumulative sum of final_pnl
    let cumulative = 0;
    const lineData = ascendingTrades.map((t, idx) => {
      const finalPnl = safeNumber(t.final_pnl);
      cumulative += finalPnl;
      return {
        name: formatDate(t.exit_time) || `T${idx + 1}`,
        trailingPnl: parseInt(cumulative),
      };
    });

    // barChartData: percent difference ignoring qty = ((exit - entry)/entry)*100
    const barData = ascendingTrades.map((t, idx) => {
      const entryP = safeNumber(t.entry_price);
      const exitP = safeNumber(t.exit_price);
      const diffPercent = entryP === 0 ? 0 : ((exitP - entryP) / entryP) * 100;
      return {
        name: formatDate(t.exit_time) || `T${idx + 1}`,
        percentPnl: diffPercent.toFixed(2),
      };
    });

    setLineChartData(lineData);
    setBarChartData(barData);
  }, [historicalTrades]);

  // ---------- Sort & Paginate Trades for Table ----------
  const allTrades = (historicalTrades || []).slice();
  // Descending by exit_time for table
  allTrades.sort(
    (a, b) => getTimestamp(b.exit_time) - getTimestamp(a.exit_time)
  );

  const startIndex = page * pageSize;
  const endIndex = startIndex + pageSize;
  const currentTrades = allTrades.slice(startIndex, endIndex);
  const totalPages = Math.ceil(allTrades.length / pageSize);

  // ---------- Stats Display ----------
  const displayedHistTotalPnl = histTotalPnl.toFixed(2);
  const displayedMaxDD = maxDrawdown.toFixed(2);
  const displayedHighCap = highestCapitalUsed.toFixed(2);
  const displayedAccuracy = (accuracy * 100).toFixed(2);
  const displayedRR = riskReward.toFixed(2);
  const displayedAvgProfit = avgProfit.toFixed(2);
  const displayedAvgLoss = avgLoss.toFixed(2);
  const displayedAvgPnl = avgPnl.toFixed(2);
  const displayedPF = Number.isFinite(profitFactor)
    ? profitFactor.toFixed(2)
    : "∞";

  return (
    <Box sx={{ color: "white", px: isMobile ? 2 : 4, py: 3 }}>
      {/* HISTORICAL TRADES STATS ROW */}
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 3,
          mb: 3,
          // 1) Center on phone, left on desktop
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
              color: histTotalPnl >= 0 ? "#22c55e" : "#ef4444",
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
              color: avgPnl >= 0 ? "#22c55e" : "#ef4444",
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
              color: profitFactor >= 1 ? "#22c55e" : "#ef4444",
              fontSize: "1rem",
            }}
          >
            {displayedPF}
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
                <Bar dataKey="percentPnl" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Grid>
      </Grid>

      {/* BOTTOM AREA: Paginated Table of historicalTrades, sorted by exit_time DESC */}
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
                        {finalPnl.toFixed(2)}
                      </TableCell>
                      <TableCell>{highestQty}</TableCell>
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
                  sx={{
                    backgroundColor: "#1e1e1e",
                    borderRadius: 1,
                    p: 2,
                  }}
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
                      {finalPnl.toFixed(2)}
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
                    <Typography variant="caption">{highestQty}</Typography>
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
