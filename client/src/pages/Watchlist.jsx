import React, { useEffect, useState, useRef, useContext, useCallback } from "react";
import { toast } from "sonner";
import api from "../utils/api"; // Adjust as necessary
import {
  Button,
  ButtonGroup,
  Spinner,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
} from "@nextui-org/react";

import { DataContext } from "../utils/DataContext";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode";

import BuyModal from "../components/BuyModal";
import SellModal from "../components/SellModal";
import ChartModal from "../components/ChartModal";
import AddAlertModal from "../components/AddAlertModal";
import AddWatchlistModal from "../components/AddWatchlistModal";

import SideChart from "../components/SideChart";

function Watchlist() {
  // -------------------------------------------------------
  // CONTEXTS & STATE
  // -------------------------------------------------------
  const { liveData, riskpool, watchlistAlerts } = useContext(DataContext);
  const { token } = useContext(AuthContext);

  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token);
      userRole = decoded.role || "";
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  const [watchlists, setWatchlists] = useState([]);
  const [selectedWatchlist, setSelectedWatchlist] = useState(null);
  const [watchlistEntries, setWatchlistEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const searchContainerRef = useRef(null);
  const chartContainerRef = useRef(null);

  // -------------------------------------------------------
  // MODAL STATES & DATA
  // -------------------------------------------------------
  const [isBuyModalOpen, setIsBuyModalOpen] = useState(false);
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [isAddAlertModalOpen, setIsAddAlertModalOpen] = useState(false);
  const [isAddWatchlistModalOpen, setIsAddWatchlistModalOpen] = useState(false);

  const [buyData, setBuyData] = useState(null);
  const [sellData, setSellData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [addAlertData, setAddAlertData] = useState(null);

  // -------------------------------------------------------
  // MODAL HANDLERS
  // -------------------------------------------------------
  const handleOpenBuyModal = () => setIsBuyModalOpen(true);
  const handleCloseBuyModal = () => setIsBuyModalOpen(false);
  const handleOpenSellModal = () => setIsSellModalOpen(true);
  const handleCloseSellModal = () => setIsSellModalOpen(false);
  const handleOpenChartModal = () => setIsChartModalOpen(true);
  const handleCloseChartModal = () => setIsChartModalOpen(false);
  const handleOpenAddAlertModal = () => setIsAddAlertModalOpen(true);
  const handleCloseAddAlertModal = () => setIsAddAlertModalOpen(false);
  const handleOpenAddWatchlistModal = () => setIsAddWatchlistModalOpen(true);
  const handleCloseAddWatchlistModal = () => setIsAddWatchlistModalOpen(false);

  // Add a function to handle adding alerts from the chart modal
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

  // -------------------------------------------------------
  // FETCH WATCHLIST NAMES ON MOUNT
  // -------------------------------------------------------
  useEffect(() => {
    fetchWatchlistNames();
  }, []);

  const fetchWatchlistNames = async () => {
    setIsLoading(true);
    try {
      const response = await api.get("/api/watchlist/watchlistname/");
      let wls = response.data || [];

      if (wls.length === 0) {
        try {
          await createDefaultWatchlist();
          const newResponse = await api.get("/api/watchlist/watchlistname/");
          wls = newResponse.data || [];
        } catch (createError) {
          console.error("Error creating default watchlist:", createError);
          toast.error("Failed to create default watchlist.");
        }
      }

      const defaultWl = wls.find((wl) => wl.name === "Default");
      if (!defaultWl && wls.length > 0) {
        try {
          await createDefaultWatchlist();
          const newResponse = await api.get("/api/watchlist/watchlistname/");
          wls = newResponse.data || [];
        } catch (createError) {
          console.error("Error creating default watchlist:", createError);
          toast.error("Failed to create default watchlist.");
        }
      }

      setWatchlists(wls);

      if (!selectedWatchlist && wls.length > 0) {
        const finalDefault = wls.find((wl) => wl.name === "Default") || wls[0];
        if (finalDefault) {
          handleSelectWatchlist(finalDefault);
        }
      }
    } catch (error) {
      console.error("Error fetching watchlists:", error);
      toast.error("Failed to fetch watchlists. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const createDefaultWatchlist = async () => {
    try {
      await api.post("/api/watchlist/watchlistname/add", { name: "Default" });
      return true;
    } catch (error) {
      console.error("Error creating default watchlist:", error);
      return false;
    }
  };

  // -------------------------------------------------------
  // FETCH ENTRIES WHEN WATCHLIST IS SELECTED
  // -------------------------------------------------------
  const handleSelectWatchlist = async (wl) => {
    if (!wl || !wl.name) {
      toast.error("Invalid watchlist selected");
      return;
    }

    setSelectedWatchlist(wl);
    setIsLoading(true);
    try {
      const response = await api.get(`/api/watchlist/${wl.name}`);
      if (response && response.data) {
        setWatchlistEntries(response.data);
      } else {
        setWatchlistEntries([]);
        toast.warning(`No entries found in ${wl.name} watchlist`);
      }
    } catch (error) {
      console.error(`Error fetching entries for watchlist ${wl.name}:`, error);
      toast.error("Failed to load watchlist entries. Please try again.");
      setWatchlistEntries([]);
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------
  // DEBOUNCED SEARCH
  // -------------------------------------------------------
  useEffect(() => {
    if (!searchQuery) {
      setSearchResults([]);
      return;
    }
    const delayDebounceFn = setTimeout(async () => {
      try {
        const res = await api.get(`/api/watchlist/search/${searchQuery}`);
        setSearchResults(res.data);
      } catch (error) {
        console.error("Error searching stocks:", error);
      }
    }, 500);
    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  // -------------------------------------------------------
  // ADD STOCK TO WATCHLIST
  // -------------------------------------------------------
  const handleAddStock = async (instrument_token, symbol) => {
    setIsLoading(true);
    try {
      let targetWatchlistName = "Default";
      if (watchlists.length > 0) {
        targetWatchlistName =
          selectedWatchlist?.name || watchlists[0].name || "Default";
      } else {
        await createDefaultWatchlist();
        await fetchWatchlistNames();
      }
      await api.post("/api/watchlist/add", {
        watchlist_name: targetWatchlistName,
        instrument_token,
        symbol,
      });

      toast.success(`Added ${symbol} to ${targetWatchlistName}!`);
      if (selectedWatchlist?.name === targetWatchlistName) {
        handleSelectWatchlist(selectedWatchlist);
      }
    } catch (error) {
      console.error("Error adding stock to watchlist:", error);
      toast.error("Failed to add stock.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteEntry = async (entry) => {
    setIsLoading(true);
    try {
      await api.delete("/api/watchlist/remove", {
        params: {
          watchlist_name: selectedWatchlist.name,
          instrument_token: entry.instrument_token,
        },
      });
      toast.success(`Deleted ${entry.symbol} from ${selectedWatchlist.name}!`);
      handleSelectWatchlist(selectedWatchlist);
    } catch (error) {
      console.error("Error deleting stock from watchlist:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------
  // DELETE WATCHLIST (ADMIN ONLY)
  // -------------------------------------------------------
  const handleDeleteWatchlist = async () => {
    if (!selectedWatchlist) return;

    setIsLoading(true);
    try {
      await api.delete(
        `/api/watchlist/watchlistname/remove/${selectedWatchlist.id}`
      );
      toast.success(`Deleted watchlist: ${selectedWatchlist.name}`);
      setSelectedWatchlist(null);
      await fetchWatchlistNames();
    } catch (error) {
      console.error("Error deleting watchlist:", error);
      toast.error("Failed to delete watchlist.");
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------
  // HIDE SEARCH RESULTS ON CLICK OUTSIDE
  // -------------------------------------------------------
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(e.target)
      ) {
        setSearchResults([]);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // -------------------------------------------------------
  // MERGE LIVE DATA INTO WATCHLIST ENTRIES
  // -------------------------------------------------------
  useEffect(() => {
    if (
      !watchlistEntries ||
      !watchlistEntries.length ||
      !liveData ||
      !liveData.length
    )
      return;

    const mergedEntries = watchlistEntries.map((entry) => {
      if (!entry || typeof entry !== "object") return entry;

      const liveItem = liveData.find(
        (ld) => ld && ld.instrument_token === entry.instrument_token
      );

      if (liveItem) {
        return {
          ...entry,
          last_price: liveItem.last_price || entry.last_price || 0,
          change:
            liveItem.change !== undefined ? liveItem.change : entry.change || 0,
          prevClose: liveItem?.ohlc?.close || entry.prevClose || 0,
        };
      }
      return entry;
    });

    setWatchlistEntries(mergedEntries);
  }, [liveData]);

  // -------------------------------------------------------
  // POPULATE DATA FOR MODALS
  // -------------------------------------------------------
  const populateBuyData = (row) => {
    setBuyData({
      symbol: row.symbol,
      instrument_token: row.instrument_token,
      available_risk: riskpool?.available_risk,
      used_risk: riskpool?.used_risk,
      last_price: row.last_price,
    });
  };

  const populateSellData = (row) => {
    setSellData({
      symbol: row.symbol,
      instrument_token: row.instrument_token,
      available_risk: riskpool?.available_risk,
      used_risk: riskpool?.used_risk,
      last_price: row.last_price,
    });
  };

  const populateChartData = (row) => {
    setChartData({
      symbol: row.symbol,
      token: row.instrument_token,
    });
  };

  const populateAddAlertData = (row) => {
    setAddAlertData({
      symbol: row.symbol,
      instrument_token: row.instrument_token,
      ltp: row.last_price,
    });
  };

  // -------------------------------------------------------
  // LISTEN FOR REAL-TIME WATCHLIST ALERTS
  // -------------------------------------------------------
  useEffect(() => {
    if (watchlistAlerts) {
      fetchWatchlistNames();
      if (selectedWatchlist) {
        handleSelectWatchlist(selectedWatchlist);
      }
    }
  }, [watchlistAlerts]);

  // -------------------------------------------------------
  // RENDER
  // -------------------------------------------------------
  return (
    <div className="w-full px-6 text-white relative">
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
      <AddWatchlistModal
        isOpen={isAddWatchlistModalOpen}
        onClose={handleCloseAddWatchlistModal}
        onWatchlistAdded={fetchWatchlistNames}
      />

      {/* Top Controls and Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between my-3">
        <div className="flex items-center gap-3">
          <Button
            size="md"
            color="success"
            variant="flat"
            className="min-w-[150px] h-10 px-4 bg-green-500/20 hover:bg-green-500/30 text-green-500"
            onPress={() => {
              if (selectedWatchlist) {
                handleSelectWatchlist(selectedWatchlist);
              }
            }}
          >
            Refresh Watchlist
          </Button>
          <select
            className="h-10 px-4 py-1 text-sm text-white rounded-md border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-green-500 shadow-md"
            value={selectedWatchlist?.id || ""}
            onChange={(e) => {
              const found = watchlists.find(
                (wl) => wl.id === parseInt(e.target.value, 10)
              );
              if (found) {
                handleSelectWatchlist(found);
              }
            }}
          >
            <option value="" disabled>
              Select watchlist
            </option>
            {watchlists.map((wl) => (
              <option key={wl.id} value={wl.id}>
                {wl.name}
              </option>
            ))}
          </select>
          <Button
            size="md"
            color="primary"
            variant="flat"
            className="h-10 px-3 bg-blue-500/20 hover:bg-blue-500/30 text-blue-500"
            onPress={handleOpenAddWatchlistModal}
          >
            Add Watchlist
          </Button>
          {userRole === "admin" && selectedWatchlist && (
            <Button
              size="md"
              color="danger"
              variant="flat"
              className="h-10 px-3 bg-red-500/20 hover:bg-red-500/30 text-red-500"
              onPress={handleDeleteWatchlist}
            >
              Delete Watchlist
            </Button>
          )}
        </div>

        {watchlistEntries && (
          <span className="text-sm mt-2 sm:mt-0 font-medium text-zinc-300">
            Watchlist Count:{" "}
            <span className="text-white font-semibold">
              {watchlistEntries.length}
            </span>
          </span>
        )}
      </div>

      {/* Layout container */}
      <div className="flex flex-col md:flex-row h-[calc(100vh-190px)] gap-6">
        {/* LEFT SIDE: Search + Watchlist Entries */}
        <div className="relative w-full md:w-1/2 lg:w-1/3 h-full">
          {/* Search input */}
          <div ref={searchContainerRef} className="relative mb-4 w-full">
            <span className="absolute -translate-y-1/2 left-3 top-1/2 text-zinc-500">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-4.35-4.35m0 0a8.5 8.5 0 1 0-12.04 0 8.5 8.5 0 0 0 12.04 0z"
                />
              </svg>
            </span>
            <input
              type="text"
              placeholder="Search stocks to add..."
              className="w-full h-10 pl-10 pr-2 rounded-md bg-zinc-800/70 backdrop-blur-sm border border-zinc-700 text-zinc-300 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-green-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchResults.length > 0 && (
              <div className="absolute left-0 z-10 w-full mt-1 border rounded top-12 bg-zinc-800 border-zinc-700 max-h-[60vh] overflow-y-auto custom-scrollbar">
                {searchResults.map((stock) => {
                  const displayName = stock.tradingsymbol || stock.company_name;
                  return (
                    <div
                      key={stock.instrument_token}
                      className="flex items-center justify-between h-10 px-2 border-b cursor-pointer border-zinc-700 hover:bg-zinc-700"
                      onClick={() =>
                        handleAddStock(stock.instrument_token, displayName)
                      }
                    >
                      <span className="flex items-center text-sm text-zinc-200">
                        {displayName}
                        <span className="ml-2 text-xs text-zinc-400">
                          {stock.exchange || ""}
                        </span>
                      </span>
                      <button className="flex items-center text-blue-400 hover:text-blue-300">
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
                            d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                          />
                        </svg>
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Watchlist Table with Glassmorphism effect */}
          {isLoading ? (
            <div className="flex flex-col justify-center items-center w-full h-[calc(100%-60px)]">
              <Spinner size="lg" />
              <span className="m-5 text-2xl">Loading Watchlist Data</span>
            </div>
          ) : selectedWatchlist ? (
            watchlistEntries.length > 0 ? (
              <div className="w-full h-[calc(100%-60px)] overflow-auto custom-scrollbar">
                <Table
                  aria-label="Watchlist table"
                  className="w-full no-scrollbar"
                  align="center"
                  radius="lg"
                  shadow="md"
                  isStriped
                  classNames={{
                    base: "bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden",
                    thead: "bg-zinc-900 border-b border-zinc-800",
                    th: "text-zinc-400 font-medium text-xs py-3 px-4 uppercase tracking-wider",
                    td: "py-3 px-4 text-white/90",
                    tr: "border-b border-zinc-800/50",
                  }}
                >
                  <TableHeader>
                    <TableColumn className="w-[25%]">Symbol</TableColumn>
                    <TableColumn className="w-[25%] text-center">
                      Last Price
                    </TableColumn>
                    <TableColumn className="w-[25%] text-center">
                      Change
                    </TableColumn>
                    <TableColumn className="w-[25%] text-center">
                      Actions
                    </TableColumn>
                  </TableHeader>
                  <TableBody>
                    {watchlistEntries.map((entry) => {
                      const colorClass =
                        entry.change > 0
                          ? "text-green-500"
                          : entry.change < 0
                          ? "text-red-500"
                          : "text-zinc-400";
                      const priceDiff = entry.last_price - entry.prevClose || 0;
                      return (
                        <TableRow key={entry.id}>
                          <TableCell>{entry.symbol}</TableCell>
                          <TableCell className="text-center">
                            {entry.last_price?.toFixed(2) || "--"}
                          </TableCell>
                          <TableCell className={`${colorClass} text-center`}>
                            {entry.change?.toFixed(2) || "0.00"}%
                            <span className="ml-1 text-xs">
                              ({priceDiff.toFixed(2)})
                            </span>
                          </TableCell>
                          <TableCell className="text-center">
                            <ButtonGroup className="shadow-sm">
                              {userRole === "admin" && (
                                <>
                                  <Button
                                    size="sm"
                                    color="success"
                                    variant="flat"
                                    className="min-w-[40px] h-9 px-3 bg-green-500/20 hover:bg-green-500/30 text-green-500"
                                    onPress={() => {
                                      populateBuyData(entry);
                                      handleOpenBuyModal();
                                    }}
                                  >
                                    En
                                  </Button>
                                  <Button
                                    size="sm"
                                    color="danger"
                                    variant="flat"
                                    className="min-w-[40px] h-9 px-3 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                                    onPress={() => {
                                      populateSellData(entry);
                                      handleOpenSellModal();
                                    }}
                                  >
                                    Ex
                                  </Button>
                                  <Button
                                    size="sm"
                                    color="primary"
                                    variant="flat"
                                    className="min-w-[40px] h-9 bg-blue-500/20 hover:bg-blue-500/30 text-blue-500"
                                    onPress={() => {
                                      populateAddAlertData(entry);
                                      handleOpenAddAlertModal();
                                    }}
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
                                        d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0M3.124 7.5A8.969 8.969 0 0 1 5.292 3m13.416 0a8.969 8.969 0 0 1 2.168 4.5"
                                      />
                                    </svg>
                                  </Button>
                                </>
                              )}
                              <Button
                                size="sm"
                                color="warning"
                                variant="flat"
                                className="min-w-[40px] h-9 bg-amber-500/20 hover:bg-amber-500/30 text-amber-500"
                                onPress={() => {
                                  populateChartData(entry);
                                  if (chartContainerRef.current) {
                                    chartContainerRef.current.scrollIntoView({
                                      behavior: "smooth",
                                      block: "start",
                                    });
                                  }
                                }}
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
                              </Button>
                              <Button
                                size="sm"
                                color="danger"
                                variant="flat"
                                className="min-w-[40px] h-9 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                                onPress={() => {
                                  handleDeleteEntry(entry);
                                }}
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
                                    d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                                  />
                                </svg>
                              </Button>
                            </ButtonGroup>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="flex justify-center items-center h-[calc(100%-60px)] bg-zinc-900/50 border border-zinc-800 rounded-xl text-zinc-400">
                No entries in this watchlist. Search and add stocks above.
              </div>
            )
          ) : (
            <div className="flex justify-center items-center h-[calc(100%-60px)] bg-zinc-900/50 border border-zinc-800 rounded-xl text-zinc-400">
              No watchlist selected. Please select or create a watchlist.
            </div>
          )}
        </div>

        {/* RIGHT SIDE: The Chart */}
        <div
          className="w-full md:w-1/2 lg:w-2/3 h-full bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden"
          ref={chartContainerRef}
        >
          <SideChart symbol={chartData?.symbol} token={chartData?.token} />
        </div>
      </div>

      {/* Custom Scrollbar Styles */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: #6b7280; /* medium gray */
          border-radius: 9999px; /* rounded */
          border: 2px solid transparent;
          background-clip: content-box;
        }
        .custom-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: #6b7280 transparent;
        }
      `}</style>
    </div>
  );
}

export default Watchlist;
