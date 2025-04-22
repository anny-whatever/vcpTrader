import React, { useContext, useState } from "react";
import { DataContext } from "../utils/DataContext";
import {
  Box,
  Typography,
  Paper,
  Chip,
  IconButton,
  Button,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Card,
  Alert,
  useTheme,
  alpha,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import { Toaster, toast } from "sonner";
import api from "../utils/api";
import { PlayToastSound, PlayErrorSound } from "../utils/PlaySound";
import ChartModal from "../components/ChartModal";

export default function Alerts() {
  const { priceAlerts, liveData } = useContext(DataContext);
  const navigate = useNavigate();
  const theme = useTheme();
  
  const [deletingId, setDeletingId] = useState(null);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [chartData, setChartData] = useState(null);

  // Get current prices from liveData
  const getCurrentPrice = (instrumentToken) => {
    if (!liveData) return null;
    
    const tickData = liveData.find(
      (tick) => tick.instrument_token === instrumentToken
    );
    
    return tickData ? tickData.last_price : null;
  };
  
  // Calculate percentage difference
  const calculateDifference = (alertPrice, currentPrice) => {
    if (!currentPrice) return null;
    
    const difference = ((currentPrice - alertPrice) / alertPrice) * 100;
    return difference.toFixed(2);
  };

  // Handle delete alert
  const handleDeleteAlert = async (alertId) => {
    try {
      setDeletingId(alertId);
      await api.delete("/api/alerts/remove", { params: { alert_id: alertId } });
      PlayToastSound();
      toast.success("Alert removed successfully", {
        duration: 5000,
      });
    } catch (error) {
      PlayErrorSound();
      toast.error("Failed to delete alert", {
        duration: 5000,
      });
      console.error("Error deleting alert:", error);
    } finally {
      setDeletingId(null);
    }
  };

  // Chart modal handlers
  const handleOpenChartModal = () => setIsChartModalOpen(true);
  const handleCloseChartModal = () => setIsChartModalOpen(false);

  // Open chart modal with the symbol and token
  const openChartModal = (symbol, instrumentToken) => {
    setChartData({
      symbol: symbol,
      token: instrumentToken
    });
    handleOpenChartModal();
  };

  if (!priceAlerts || priceAlerts.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ mb: 3 }}>Price Alerts</Typography>
        <Card sx={{ p: 4, textAlign: "center", backgroundColor: alpha(theme.palette.background.paper, 0.7) }}>
          <Box sx={{ mb: 2 }}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="64"
              height="64"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ margin: "0 auto" }}
            >
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
          </Box>
          <Typography variant="h6" sx={{ mb: 1 }}>No Price Alerts</Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            You haven't set any price alerts yet. Add alerts from the watchlist to get notified when a stock reaches your target price.
          </Typography>
          <Button 
            variant="outlined" 
            color="primary" 
            onClick={() => navigate("/watchlist")}
          >
            Go to Watchlist
          </Button>
        </Card>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Chart Modal */}
      <ChartModal
        isOpen={isChartModalOpen}
        onClose={handleCloseChartModal}
        symbol={chartData?.symbol}
        token={chartData?.token}
      />
      
      <Typography variant="h4" sx={{ mb: 3 }}>Price Alerts</Typography>
      
      <TableContainer component={Paper} sx={{ mb: 4, backgroundColor: alpha(theme.palette.background.paper, 0.7) }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Symbol</TableCell>
              <TableCell>Alert Type</TableCell>
              <TableCell>Alert Price</TableCell>
              <TableCell>Current Price</TableCell>
              <TableCell>Difference</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {priceAlerts.map((alert) => {
              const currentPrice = getCurrentPrice(alert.instrument_token);
              const difference = calculateDifference(alert.price, currentPrice);
              
              return (
                <TableRow key={alert.id}>
                  <TableCell component="th" scope="row">
                    <Typography variant="body1" fontWeight="medium">
                      {alert.symbol}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={alert.alert_type === "sl" ? "Stop Loss" : "Target"}
                      size="small"
                      sx={{
                        bgcolor: alert.alert_type === "sl" ? "#ef4444" : "#22c55e",
                        color: "white",
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      ₹{alert.price.toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {currentPrice ? (
                      <Typography variant="body2" fontWeight="medium">
                        ₹{currentPrice.toFixed(2)}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        --
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {difference ? (
                      <Chip
                        label={`${difference}%`}
                        size="small"
                        sx={{
                          bgcolor: parseFloat(difference) >= 0 ? "#22c55e" : "#ef4444",
                          color: "white",
                        }}
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        --
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                      <IconButton
                        color="primary"
                        onClick={() => openChartModal(alert.symbol, alert.instrument_token)}
                        size="small"
                        sx={{ mr: 1 }}
                      >
                        <ShowChartIcon />
                      </IconButton>
                      <IconButton
                        color="error"
                        onClick={() => handleDeleteAlert(alert.id)}
                        disabled={deletingId === alert.id}
                        size="small"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      
      <Alert severity="info" sx={{ mb: 3, backgroundColor: alpha(theme.palette.info.main, 0.1) }}>
        <Typography variant="body2">
          Price alerts will be triggered automatically when the price conditions are met. 
          Click on the chart icon to view the stock chart.
        </Typography>
      </Alert>
    </Box>
  );
} 