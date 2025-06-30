// Screener.jsx
import React, {
  useState,
  useEffect,
  useContext,
  useMemo,
  useCallback,
  useRef,
} from "react";
import { DataContext } from "../utils/DataContext";
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button as NextUIButton,
  ButtonGroup,
  Spinner,
  Pagination,
} from "@nextui-org/react";
import BuyModal from "../components/BuyModal";
import SellModal from "../components/SellModal";
import ChartModal from "../components/ChartModal";
import AddAlertModal from "../components/AddAlertModal"; // New modal for adding alert
import StockDetailModal from "../components/StockDetailModal"; // New modal for stock details
import RiskMeter from "../components/RiskMeter"; // Risk meter component
import api from "../utils/api";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode"; // ✅ Correct import
import { Box, Typography, Button } from "@mui/material";
import { calculateRiskScores } from "../utils/api.js";

function Screener() {
  const { liveData, riskpool } = useContext(DataContext);
  const { token, logout } = useContext(AuthContext);
  const screenOptions = ["VCP"];
  const [screenerData, setScreenerData] = useState(null);
  const [screen, setScreen] = useState("VCP");
  const previousScreenRef = useRef(screen);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(50);

  // Modals for buy, sell, chart, add alert, and stock details
  const [isBuyModalOpen, setIsBuyModalOpen] = useState(false);
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [isAddAlertModalOpen, setIsAddAlertModalOpen] = useState(false);
  const [isStockDetailModalOpen, setIsStockDetailModalOpen] = useState(false);

  // Data for modals
  const [buyData, setBuyData] = useState(null);
  const [sellData, setSellData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [addAlertData, setAddAlertData] = useState(null);
  const [stockDetailData, setStockDetailData] = useState(null);

  // Current selected stock index for navigation
  const [currentStockIndex, setCurrentStockIndex] = useState(null);



  // Risk calculation state
  const [isCalculatingRisk, setIsCalculatingRisk] = useState(false);

  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token); // ✅ Use named import
      userRole = decoded.role || "";
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // Reset to first page when screen changes
  useEffect(() => {
    setCurrentPage(1);
  }, [screen]);

  // Fetch screener data
  const fetchScreenerData = useCallback(async () => {
    if (previousScreenRef.current !== screen) {
      previousScreenRef.current = screen;
      setScreenerData(null);
      setCurrentPage(1); // Reset to first page when screen changes
    }

    try {
      let response;
      // Determine endpoint based on screen
      // Only VCP screener available now
      const endpoint = "/api/screener/vcpscreen";

      // Single API call with the determined endpoint
      response = await api.get(endpoint);

      // Use requestAnimationFrame to schedule state update in next frame
      if (response?.data) {
        requestAnimationFrame(() => {
          setScreenerData(response.data);
        });
      }
    } catch (error) {
      console.error(`Error fetching ${screen} data:`, error);
    }
  }, [screen]);

  useEffect(() => {
    fetchScreenerData();
  }, [fetchScreenerData]);

  // Add periodic refresh during market hours for live updates
  useEffect(() => {
    const isMarketHours = () => {
      const now = new Date();
      const hours = now.getHours();
      const minutes = now.getMinutes();
      const currentTime = hours * 100 + minutes;
      // Market hours: 9:15 AM to 3:30 PM
      return currentTime >= 915 && currentTime <= 1530;
    };

    let intervalId;
    if (isMarketHours()) {
      // Refresh screener data every 2 minutes during market hours
      intervalId = setInterval(() => {
        fetchScreenerData();
      }, 2 * 60 * 1000); // 2 minutes
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [fetchScreenerData]);

  // Merge live data into screener data and force React to detect changes
  useEffect(() => {
    if (screenerData && liveData) {
      let hasUpdates = false;
      
      screenerData.forEach((stock) => {
        const liveDataItem = liveData.find(
          (liveItem) => liveItem.instrument_token === stock.instrument_token
        );
        if (liveDataItem) {
          // Check if we have actual updates to avoid unnecessary re-renders
          const oldPrice = stock.last_price;
          const oldChange = stock.change;
          
          // Update last_price directly from live data
          stock.last_price = liveDataItem.last_price;
          stock.current_price = liveDataItem.last_price;
          
          // Update change percentage if available in live data
          if (liveDataItem.change !== undefined) {
            stock.change = liveDataItem.change;
          }
          
          // Update ATR if available
          if (liveDataItem.atr !== undefined) {
            stock.atr = liveDataItem.atr;
          }
          
          // Check if we had actual changes
          if (oldPrice !== stock.last_price || oldChange !== stock.change) {
            hasUpdates = true;
          }
        }
      });
      
      // Force React to re-render by updating state if we had changes
      if (hasUpdates) {
        setScreenerData([...screenerData]);
      }
    }
  }, [screenerData, liveData]);

  // Memoize sorted screener data
  const sortedScreenerData = useMemo(() => {
    if (!screenerData) return screenerData;
    
    // Always sort by breakout date (latest first) and quality score (highest first)
    return [...screenerData].sort((a, b) => {
      // First sort by breakout_date (latest first)
      const dateA = new Date(a.breakout_date || 0);
      const dateB = new Date(b.breakout_date || 0);
      if (dateB.getTime() !== dateA.getTime()) {
        return dateB.getTime() - dateA.getTime();
      }
      // If dates are equal, sort by quality_score (highest first)
      return (b.quality_score || 0) - (a.quality_score || 0);
    });
  }, [screenerData]);

  // Calculate pagination values
  const paginatedData = useMemo(() => {
    if (!sortedScreenerData) return null;

    const indexOfLastItem = currentPage * itemsPerPage;
    const indexOfFirstItem = indexOfLastItem - itemsPerPage;

    return sortedScreenerData.slice(indexOfFirstItem, indexOfLastItem);
  }, [sortedScreenerData, currentPage, itemsPerPage]);

  // Calculate total pages
  const totalPages = useMemo(() => {
    if (!sortedScreenerData) return 0;
    return Math.ceil(sortedScreenerData.length / itemsPerPage);
  }, [sortedScreenerData, itemsPerPage]);

  // Handle page change
  const handlePageChange = useCallback((page) => {
    // Use requestAnimationFrame to avoid layout thrashing
    requestAnimationFrame(() => {
      setCurrentPage(page);
      // Scroll to top when page changes
      window.scrollTo(0, 0);
    });
  }, []);



  // Memoize handlers to prevent recreating functions on each render
  const populateBuyData = useCallback(
    (row) => {
      setBuyData({
        symbol: row.symbol,
        instrument_token: row.instrument_token,
        available_risk: riskpool?.available_risk,
        used_risk: riskpool?.used_risk,
        last_price: row.last_price,
      });
    },
    [riskpool]
  );

  const populateSellData = useCallback(
    (row) => {
      setSellData({
        symbol: row.symbol,
        instrument_token: row.instrument_token,
        available_risk: riskpool?.available_risk,
        used_risk: riskpool?.used_risk,
        last_price: row.last_price,
      });
    },
    [riskpool]
  );

  const populateChartData = useCallback(
    (row, index) => {
      // Convert relative index (in current page) to absolute index in full dataset
      const absoluteIndex = (currentPage - 1) * itemsPerPage + index;

      setChartData({
        symbol: row.symbol,
        token: row.instrument_token,
      });
      setCurrentStockIndex(absoluteIndex);
    },
    [currentPage, itemsPerPage]
  );

  const populateAddAlertData = useCallback((row) => {
    setAddAlertData({
      symbol: row.symbol,
      instrument_token: row.instrument_token,
      ltp: row.last_price,
    });
  }, []);

  const populateStockDetailData = useCallback((row) => {
    setStockDetailData(row);
  }, []);

  // Modal Handlers - memoized
  const handleOpenBuyModal = useCallback(() => setIsBuyModalOpen(true), []);
  const handleCloseBuyModal = useCallback(() => setIsBuyModalOpen(false), []);

  const handleOpenSellModal = useCallback(() => setIsSellModalOpen(true), []);
  const handleCloseSellModal = useCallback(() => setIsSellModalOpen(false), []);

  const handleOpenChartModal = useCallback(() => setIsChartModalOpen(true), []);
  const handleCloseChartModal = useCallback(
    () => setIsChartModalOpen(false),
    []
  );

  const handleOpenAddAlertModal = useCallback(
    () => setIsAddAlertModalOpen(true),
    []
  );
  const handleCloseAddAlertModal = useCallback(
    () => setIsAddAlertModalOpen(false),
    []
  );

  const handleOpenStockDetailModal = useCallback(
    () => setIsStockDetailModalOpen(true),
    []
  );
  const handleCloseStockDetailModal = useCallback(
    () => setIsStockDetailModalOpen(false),
    []
  );

  // Navigate to previous stock in the list - memoized
  const handlePreviousStock = useCallback(() => {
    if (currentStockIndex > 0 && screenerData) {
      const prevIndex = currentStockIndex - 1;
      const prevStock = screenerData[prevIndex];
      setChartData({
        symbol: prevStock.symbol,
        token: prevStock.instrument_token,
      });
      setCurrentStockIndex(prevIndex);
    }
  }, [currentStockIndex, screenerData]);

  // Navigate to next stock in the list - memoized
  const handleNextStock = useCallback(() => {
    if (currentStockIndex < screenerData?.length - 1 && screenerData) {
      const nextIndex = currentStockIndex + 1;
      const nextStock = screenerData[nextIndex];
      setChartData({
        symbol: nextStock.symbol,
        token: nextStock.instrument_token,
      });
      setCurrentStockIndex(nextIndex);
    }
  }, [currentStockIndex, screenerData]);

  // Add a function to handle adding alerts from the chart modal - memoized
  const handleAddAlertFromChart = useCallback(
    (symbol, instrument_token, ltp) => {
      setAddAlertData({
        symbol,
        instrument_token,
        ltp,
      });
      setIsAddAlertModalOpen(true);
    },
    []
  );

  // Add a function to handle buying from the chart modal
  const handleBuyFromChart = useCallback(
    (symbol, instrument_token, ltp) => {
      setBuyData({
        symbol,
        instrument_token,
        available_risk: riskpool?.available_risk,
        used_risk: riskpool?.used_risk,
        last_price: ltp,
      });
      handleOpenBuyModal();
    },
    [riskpool, handleOpenBuyModal]
  );

  // Memoize the initial setup for different screen types
  const screenChangeHandler = useCallback(
    (e) => {
      const newScreen = e.target.value;

      // Only update if actually changed
      if (newScreen !== screen) {
        // Clear current data first to avoid mixed renders
        // This prevents reflow by not showing stale data
        setScreenerData(null);

        // Schedule screen change to next task to reduce main thread blocking
        setTimeout(() => {
          setScreen(newScreen);
        }, 0);
      }
    },
    [screen]
  );

  // Memoize row action handlers
  const handleBuyAction = useCallback(
    (row) => {
      populateBuyData(row);
      handleOpenBuyModal();
    },
    [populateBuyData, handleOpenBuyModal]
  );

  const handleSellAction = useCallback(
    (row) => {
      populateSellData(row);
      handleOpenSellModal();
    },
    [populateSellData, handleOpenSellModal]
  );

  const handleChartAction = useCallback(
    (row, index) => {
      populateChartData(row, index);
      handleOpenChartModal();
    },
    [populateChartData, handleOpenChartModal]
  );

  const handleAlertAction = useCallback(
    (row) => {
      populateAddAlertData(row);
      handleOpenAddAlertModal();
    },
    [populateAddAlertData, handleOpenAddAlertModal]
  );

  const handleDetailAction = useCallback(
    (row) => {
      populateStockDetailData(row);
      handleOpenStockDetailModal();
    },
    [populateStockDetailData, handleOpenStockDetailModal]
  );

  // Add a function to calculate risk scores for all stocks in screener
  const handleCalculateRiskScores = useCallback(async () => {
    if (!screenerData || isCalculatingRisk) return;
    
    setIsCalculatingRisk(true);
    
    try {
      // Get all symbols from the screener data to recalculate risk scores for all
      const symbols = screenerData.map(stock => stock.symbol);
      console.log(`Calculating risk scores for ${symbols.length} stocks:`, symbols);
      
      const response = await calculateRiskScores(symbols);
      console.log('Risk calculation response:', response);
      
      // Show success message for thread pool execution
      alert(`Risk score calculation started in background. Processing ${symbols.length} stocks in thread pool.`);
      
      // Refresh screener data to get updated risk scores after some time
      setTimeout(() => {
        fetchScreenerData();
        setIsCalculatingRisk(false);
      }, 5000); // Give more time for thread pool calculation
      
    } catch (error) {
      console.error('Error calculating risk scores:', error);
      setIsCalculatingRisk(false);
      alert('Error starting risk calculation. Please try again.');
    }
  }, [screenerData, isCalculatingRisk, fetchScreenerData]);

  // Memoize rendering of table rows to prevent forced reflows
  const renderTableRows = useMemo(() => {
    if (!paginatedData) return null;

    return paginatedData.map((row, index) => {
      const colorClass = row.change > 0 ? "text-green-500" : "text-red-500";
      
      // Format dates
      const formatDate = (dateString) => {
        if (!dateString) return "N/A";
        try {
          return new Date(dateString).toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: '2-digit'
          });
        } catch {
          return "N/A";
        }
      };

      // Format currency
      const formatCurrency = (value) => {
        if (value == null || isNaN(value)) return "--";
        return `₹${parseFloat(value).toFixed(2)}`;
      };

      // Get quality score color
      const getQualityColor = (score) => {
        if (score >= 7) return "text-green-400";
        if (score >= 5) return "text-yellow-400";
        if (score >= 3) return "text-orange-400";
        return "text-red-400";
      };

      return (
        <TableRow key={`${row.symbol}-${index}`}>
          <TableCell className="font-medium">{row.symbol}</TableCell>
          <TableCell className="text-sm">{formatDate(row.pattern_start_date)}</TableCell>
          <TableCell className="text-sm">{formatDate(row.breakout_date)}</TableCell>
          <TableCell>
            <span className={`font-semibold ${getQualityColor(row.quality_score)}`}>
              {row.quality_score || "N/A"}
            </span>
          </TableCell>
          <TableCell className="text-sm">{formatCurrency(row.suggested_stop_loss)}</TableCell>
          <TableCell className="font-medium">{formatCurrency(row.current_price || row.entry_price)}</TableCell>
          <TableCell>
            <span className={colorClass}>
              {row.change > 0 ? "+" : ""}
              {row.change !== null && row.change !== undefined ? row.change.toFixed(2) : "0.00"}%
            </span>
          </TableCell>
          <TableCell>
            <ButtonGroup size="sm" variant="flat" className="rounded-lg">
              {userRole === "admin" && (
                <>
                  <NextUIButton
                    color="success"
                    variant="flat"
                    className="min-w-[40px] h-9 bg-green-500/20 hover:bg-green-500/30 text-green-500"
                    onPress={() => handleBuyAction(row)}
                    isDisabled={userRole !== "admin"}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M12 4.5v15m7.5-7.5h-15"
                      />
                    </svg>
                  </NextUIButton>
                  <NextUIButton
                    color="danger"
                    variant="flat"
                    className="min-w-[40px] h-9 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                    onPress={() => handleSellAction(row)}
                    isDisabled={userRole !== "admin"}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 12h14"
                      />
                    </svg>
                  </NextUIButton>
                  <NextUIButton
                    color="warning"
                    variant="flat"
                    className="min-w-[40px] h-9 bg-amber-500/20 hover:bg-amber-500/30 text-amber-500"
                    onPress={() => handleChartAction(row, index)}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                      />
                    </svg>
                  </NextUIButton>
                  <NextUIButton
                    color="primary"
                    variant="flat"
                    className="min-w-[40px] h-9 bg-blue-500/20 hover:bg-blue-500/30 text-blue-500"
                    onPress={() => handleAlertAction(row)}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
                      />
                    </svg>
                  </NextUIButton>
                  <NextUIButton
                    color="secondary"
                    variant="flat"
                    className="min-w-[40px] h-9 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400"
                    onPress={() => handleDetailAction(row)}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
                      />
                    </svg>
                  </NextUIButton>
                </>
              )}
              {userRole !== "admin" && (
                <>
                  <NextUIButton
                    size="sm"
                    color="warning"
                    variant="flat"
                    className="min-w-[40px] h-9 bg-amber-500/20 hover:bg-amber-500/30 text-amber-500"
                    onPress={() => handleChartAction(row, index)}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                      />
                    </svg>
                  </NextUIButton>
                  <NextUIButton
                    size="sm"
                    color="secondary"
                    variant="flat"
                    className="min-w-[40px] h-9 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400"
                    onPress={() => handleDetailAction(row)}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-5 h-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
                      />
                    </svg>
                  </NextUIButton>
                </>
              )}
            </ButtonGroup>
          </TableCell>
        </TableRow>
      );
    });
  }, [
    paginatedData,
    userRole,
    handleBuyAction,
    handleSellAction,
    handleChartAction,
    handleAlertAction,
    handleDetailAction,
  ]);

  // Memoize mobile card rendering
  const renderMobileCards = useMemo(() => {
    if (!paginatedData) return null;

    return paginatedData.map((row, index) => {
      const colorClass = row.change > 0 ? "text-green-500" : "text-red-500";
      
      // Format dates
      const formatDate = (dateString) => {
        if (!dateString) return "N/A";
        try {
          return new Date(dateString).toLocaleDateString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: '2-digit'
          });
        } catch {
          return "N/A";
        }
      };

      // Format currency
      const formatCurrency = (value) => {
        if (value == null || isNaN(value)) return "--";
        return `₹${parseFloat(value).toFixed(2)}`;
      };

      // Get quality score color
      const getQualityColor = (score) => {
        if (score >= 7) return "text-green-400";
        if (score >= 5) return "text-yellow-400";
        if (score >= 3) return "text-orange-400";
        return "text-red-400";
      };

      return (
        <div
          key={`${row.symbol}-mobile-${index}`}
          className="flex flex-col gap-3 p-5 bg-zinc-900/80 backdrop-blur-sm rounded-xl border border-zinc-800/70 shadow-md transition-all hover:border-zinc-700 hover:bg-zinc-800/80"
        >
          <div className="flex items-center justify-between">
            <span className="text-base font-bold text-white">{row.symbol}</span>
            <div className={`px-3 py-1 rounded-full ${row.change > 0 ? "bg-green-500/10" : "bg-red-500/10"}`}>
              <span className={`text-base font-semibold ${colorClass}`}>
                {row.change > 0 ? "+" : ""}
                {row.change !== null && row.change !== undefined ? row.change.toFixed(2) : "0.00"}%
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3 mt-1">
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Pattern Start
              </span>
              <span className="text-sm font-medium text-white">
                {formatDate(row.pattern_start_date)}
              </span>
            </div>
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Breakout Date
              </span>
              <span className="text-sm font-medium text-white">
                {formatDate(row.breakout_date)}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 mt-1">
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Quality Score
              </span>
              <span className={`text-sm font-bold ${getQualityColor(row.quality_score)}`}>
                {row.quality_score || "N/A"}
              </span>
            </div>
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Stop Loss
              </span>
              <span className="text-sm font-medium text-red-400">
                {formatCurrency(row.suggested_stop_loss)}
              </span>
            </div>
            <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
              <span className="text-xs text-zinc-400 font-medium mb-1">
                Current Price
              </span>
              <span className="text-sm font-medium text-white">
                {formatCurrency(row.current_price || row.entry_price)}
              </span>
            </div>
          </div>
          
          <div className="flex flex-col bg-zinc-950/30 p-3 rounded-lg">
            <span className="text-xs text-zinc-400 font-medium mb-1">
              Actions
            </span>
            <div className="flex mt-1">
              <ButtonGroup className="shadow-sm gap-1 flex flex-wrap">
                {userRole === "admin" && (
                  <>
                    <NextUIButton
                      size="sm"
                      color="success"
                      variant="flat"
                      className="min-w-[28px] w-7 h-7 p-0 bg-green-500/20 hover:bg-green-500/30 text-green-500"
                      onPress={() => handleBuyAction(row)}
                      isDisabled={userRole !== "admin"}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-3.5 h-3.5"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M12 4.5v15m7.5-7.5h-15"
                        />
                      </svg>
                    </NextUIButton>
                    <NextUIButton
                      size="sm"
                      color="danger"
                      variant="flat"
                      className="min-w-[28px] w-7 h-7 p-0 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                      onPress={() => handleSellAction(row)}
                      isDisabled={userRole !== "admin"}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="w-3.5 h-3.5"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 12h14"
                        />
                      </svg>
                    </NextUIButton>
                  </>
                )}
                <NextUIButton
                  size="sm"
                  color="warning"
                  variant="flat"
                  className="min-w-[28px] w-7 h-7 p-0 bg-amber-500/20 hover:bg-amber-500/30 text-amber-500"
                  onPress={() => handleChartAction(row, index)}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="w-3.5 h-3.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                    />
                  </svg>
                </NextUIButton>
                <NextUIButton
                  size="sm"
                  color="primary"
                  variant="flat"
                  className="min-w-[28px] w-7 h-7 p-0 bg-blue-500/20 hover:bg-blue-500/30 text-blue-500"
                  onPress={() => handleAlertAction(row)}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="w-3.5 h-3.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
                    />
                  </svg>
                </NextUIButton>
                <NextUIButton
                  size="sm"
                  color="secondary"
                  variant="flat"
                  className="min-w-[28px] w-7 h-7 p-0 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400"
                  onPress={() => handleDetailAction(row)}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="w-3.5 h-3.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
                    />
                  </svg>
                </NextUIButton>
              </ButtonGroup>
            </div>
          </div>
        </div>
      );
    });
  }, [
    paginatedData,
    userRole,
    handleBuyAction,
    handleSellAction,
    handleChartAction,
    handleAlertAction,
    handleDetailAction,
  ]);

  return (
    <div className="w-full px-6 text-white">
      {/* Modals */}
      <BuyModal
        isOpen={isBuyModalOpen}
        onClose={handleCloseBuyModal}
        AvailableRisk={buyData?.available_risk}
        UsedRisk={buyData?.used_risk}
        symbol={buyData?.symbol}
        ltp={buyData?.last_price}
      />
      <SellModal
        isOpen={isSellModalOpen}
        onClose={handleCloseSellModal}
        AvailableRisk={sellData?.available_risk}
        UsedRisk={sellData?.used_risk}
        symbol={sellData?.symbol}
        ltp={sellData?.last_price}
      />
      <ChartModal
        isOpen={isChartModalOpen}
        onClose={handleCloseChartModal}
        symbol={chartData?.symbol}
        token={chartData?.token}
        onPrevious={handlePreviousStock}
        onNext={handleNextStock}
        hasPrevious={currentStockIndex > 0}
        hasNext={currentStockIndex < screenerData?.length - 1}
        onAddAlert={handleAddAlertFromChart}
        onBuy={userRole === "admin" ? handleBuyFromChart : undefined}
      />
      <AddAlertModal
        isOpen={isAddAlertModalOpen}
        onClose={handleCloseAddAlertModal}
        symbol={addAlertData?.symbol}
        instrument_token={addAlertData?.instrument_token}
        ltp={addAlertData?.ltp}
      />
      <StockDetailModal
        isOpen={isStockDetailModalOpen}
        onClose={handleCloseStockDetailModal}
        stockData={stockDetailData}
      />

      {/* Top controls */}
      <div className="flex flex-col items-center justify-between my-3 sm:flex-row">
        <div className="flex items-center gap-3">
          <NextUIButton
            size="md"
            color="success"
            variant="flat"
            className="min-w-[150px] h-10 px-4 bg-green-500/20 hover:bg-green-500/30 text-green-500"
            onPress={fetchScreenerData}
          >
            Refresh Screener
          </NextUIButton>
          <NextUIButton
            size="md"
            color="primary"
            variant="flat"
            className="min-w-[170px] h-10 px-4 bg-blue-500/20 hover:bg-blue-500/30 text-blue-500"
            onPress={handleCalculateRiskScores}
            isLoading={isCalculatingRisk}
            isDisabled={isCalculatingRisk}
          >
            {isCalculatingRisk ? 'Calculating...' : 'Calculate Risk Scores'}
          </NextUIButton>
          <select
            className="h-10 px-4 py-1 text-sm text-white rounded-md border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-green-500 shadow-md"
            value={screen}
            onChange={screenChangeHandler}
          >
            {screenOptions.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </div>
        {screenerData && (
          <span className="text-sm mt-2 sm:mt-0 font-medium text-zinc-300">
            Screen Count:{" "}
            <span className="text-white font-semibold">
              {screenerData.length}
            </span>
            {totalPages > 1 && ` (Page ${currentPage} of ${totalPages})`}
          </span>
        )}
      </div>

      {/* Conditionally render table or loader */}
      {!screenerData ? (
        <div className="flex flex-col justify-center items-center w-full h-[85vh]">
          <Spinner size="lg" />
          <span className="m-5 text-2xl">Loading Screener Data</span>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden w-full md:block">
            <Table
              aria-label="Screener table"
              className="w-full no-scrollbar"
              align="center"
              radius="lg"
              shadow="md"
              isStriped
              classNames={{
                base: "bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden",
                thead: "bg-zinc-800/70 backdrop-blur-sm",
                th: "text-zinc-400 font-medium text-sm py-3 px-4",
                td: "py-3 px-4 text-white/90",
              }}
            >
              <TableHeader>
                <TableColumn>Symbol</TableColumn>
                <TableColumn>Pattern Start</TableColumn>
                <TableColumn>Breakout Date</TableColumn>
                <TableColumn>Quality Score</TableColumn>
                <TableColumn>Stop Loss</TableColumn>
                <TableColumn>Last Price</TableColumn>
                <TableColumn>Change</TableColumn>
                <TableColumn>Actions</TableColumn>
              </TableHeader>
              <TableBody>{renderTableRows}</TableBody>
            </Table>
          </div>

          {/* Mobile Card Layout */}
          <div className="block mt-4 space-y-4 md:hidden">
            {renderMobileCards}
          </div>

          {/* Pagination Controls - Updated to match dashboard style */}
          {totalPages > 1 && (
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
                variant="contained"
                size="small"
                sx={{
                  backgroundColor: "rgba(39, 39, 42, 0.5)",
                  backdropFilter: "blur(8px)",
                  minWidth: "90px",
                  height: "36px",
                  color: "white",
                  "&:hover": {
                    backgroundColor: "rgba(63, 63, 70, 0.7)",
                  },
                  borderRadius: "8px",
                  textTransform: "none",
                  fontWeight: "medium",
                  border: "1px solid rgba(63, 63, 70, 0.5)",
                  padding: "0 16px",
                }}
                disabled={currentPage === 1}
                onClick={() => handlePageChange(currentPage - 1)}
                startIcon={
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    style={{ width: "16px", height: "16px" }}
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
                  Page {currentPage} of {totalPages}
                </Typography>
              </Box>
              <Button
                variant="contained"
                size="small"
                sx={{
                  backgroundColor: "rgba(39, 39, 42, 0.5)",
                  backdropFilter: "blur(8px)",
                  minWidth: "90px",
                  height: "36px",
                  color: "white",
                  "&:hover": {
                    backgroundColor: "rgba(63, 63, 70, 0.7)",
                  },
                  borderRadius: "8px",
                  textTransform: "none",
                  fontWeight: "medium",
                  border: "1px solid rgba(63, 63, 70, 0.5)",
                  padding: "0 16px",
                }}
                disabled={currentPage >= totalPages}
                onClick={() => handlePageChange(currentPage + 1)}
                endIcon={
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    style={{ width: "16px", height: "16px" }}
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
          )}
        </>
      )}
    </div>
  );
}

// Use memo to avoid unnecessary re-renders of the entire component
export default React.memo(Screener);
