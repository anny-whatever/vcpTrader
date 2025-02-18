// src/pages/WatchlistPage.js
import React, { useEffect, useState, useRef, useContext } from "react";
import { toast } from "sonner";
import api from "../utils/api"; // Adjust as necessary
import { Button, ButtonGroup, Spinner } from "@heroui/react";

// Live Data & Riskpool (optional) from DataContext, if you use them
import { DataContext } from "../utils/DataContext";

// AuthContext to check user role (admin vs. observer)
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode"; // Make sure you have the correct import or alternative decode

// Import your modals
import BuyModal from "../components/BuyModal";
import SellModal from "../components/SellModal";
import ChartModal from "../components/ChartModal";
import AddAlertModal from "../components/AddAlertModal";
// Import the new AddWatchlistModal
import AddWatchlistModal from "../components/AddWatchlistModal";

// Import your toast sound utility (adjust path as needed)
import { PlayToastSound } from "../utils/PlaySound";

function Watchlist() {
  // -- DataContext (including watchlistAlerts for real-time updates)
  const { liveData, riskpool, watchlistAlerts } = useContext(DataContext);

  // -- AuthContext
  const { token } = useContext(AuthContext);

  // Determine user role
  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token);
      userRole = decoded.role || "";
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // -- Watchlist containers (from watchlist_name table)
  const [watchlists, setWatchlists] = useState([]);
  const [selectedWatchlist, setSelectedWatchlist] = useState(null);

  // -- Watchlist entries (from watchlist table)
  const [watchlistEntries, setWatchlistEntries] = useState([]);

  // -- Loading indicator
  const [isLoading, setIsLoading] = useState(false);

  // -- Search bar
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);

  // -- For hiding search results when clicking outside
  const searchContainerRef = useRef(null);

  // -------------------------------------------------------
  // Modals: buy, sell, chart, add alert, add watchlist
  // -------------------------------------------------------
  const [isBuyModalOpen, setIsBuyModalOpen] = useState(false);
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [isAddAlertModalOpen, setIsAddAlertModalOpen] = useState(false);
  const [isAddWatchlistModalOpen, setIsAddWatchlistModalOpen] = useState(false);

  // Data for each modal
  const [buyData, setBuyData] = useState(null);
  const [sellData, setSellData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [addAlertData, setAddAlertData] = useState(null);

  // -------------------------------------------------------
  // Modal Handlers
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

  // -------------------------------------------------------
  // 1. Fetch all watchlists on mount
  // -------------------------------------------------------
  useEffect(() => {
    fetchWatchlistNames();
  }, []);

  const fetchWatchlistNames = async () => {
    setIsLoading(true);
    try {
      const response = await api.get("/api/watchlist/watchlistname/");
      let wls = response.data;

      // If no watchlists exist, create "Default"
      if (wls.length === 0) {
        await createDefaultWatchlist();
        wls = (await api.get("/api/watchlist/watchlistname/")).data;
      }

      // If watchlists exist but no "Default" found, create it
      const defaultWl = wls.find((wl) => wl.name === "Default");
      if (!defaultWl) {
        await createDefaultWatchlist();
        wls = (await api.get("/api/watchlist/watchlistname/")).data;
      }

      setWatchlists(wls);

      // Select "Default" watchlist if none is selected
      if (!selectedWatchlist) {
        const finalDefault = wls.find((wl) => wl.name === "Default");
        if (finalDefault) {
          handleSelectWatchlist(finalDefault);
        }
      }
    } catch (error) {
      console.error("Error fetching watchlists:", error);
      toast.error("Failed to fetch watchlists.");
    } finally {
      setIsLoading(false);
    }
  };

  const createDefaultWatchlist = async () => {
    await api.post("/api/watchlist/watchlistname/add", { name: "Default" });
  };

  // -------------------------------------------------------
  // 2. When user selects a watchlist, fetch its entries
  // -------------------------------------------------------
  const handleSelectWatchlist = async (wl) => {
    setSelectedWatchlist(wl);
    setIsLoading(true);
    try {
      const response = await api.get(`/api/watchlist/${wl.name}`);
      console.log(response.data);
      setWatchlistEntries(response.data);
    } catch (error) {
      console.error("Error fetching watchlist entries:", error);
      toast.error("Failed to fetch watchlist entries.");
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------
  // 3. Debounced Search logic: fetch stocks as user types
  // -------------------------------------------------------
  useEffect(() => {
    if (!searchQuery) {
      setSearchResults([]);
      return;
    }
    const delayDebounceFn = setTimeout(async () => {
      try {
        // GET /api/watchlist/search/{query}
        const res = await api.get(`/api/watchlist/search/${searchQuery}`);
        setSearchResults(res.data);
      } catch (error) {
        console.error("Error searching stocks:", error);
      }
    }, 1000); // 1 second debounce
    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  // -------------------------------------------------------
  // 4. Add stock to watchlist
  //    If no watchlists exist, create "Default" first.
  // -------------------------------------------------------
  const handleAddStock = async (instrument_token, symbol) => {
    setIsLoading(true);
    try {
      let targetWatchlistName = "Default";
      // Use selected watchlist if available.
      if (watchlists.length > 0) {
        targetWatchlistName =
          selectedWatchlist?.name || watchlists[0].name || "Default";
      } else {
        await createDefaultWatchlist();
        await fetchWatchlistNames();
      }
      // Now add the stock to the determined watchlist.
      await api.post("/api/watchlist/add", {
        watchlist_name: targetWatchlistName,
        instrument_token,
        symbol,
      });
      PlayToastSound();
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
      toast.error("Failed to delete stock.");
    } finally {
      setIsLoading(false);
    }
  };

  // -------------------------------------------------------
  // Delete a watchlist container (only for admins)
  // -------------------------------------------------------
  const handleDeleteWatchlist = async () => {
    if (!selectedWatchlist) return;

    setIsLoading(true);
    try {
      await api.delete(
        `/api/watchlist/watchlistname/remove/${selectedWatchlist.id}`
      );
      toast.success(`Deleted watchlist: ${selectedWatchlist.name}`);
      // After deletion, refetch the watchlists.
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
  // Hide Search Results if user clicks outside
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
  // 5. Merge liveData into watchlist entries (like Screener)
  // -------------------------------------------------------
  useEffect(() => {
    if (!watchlistEntries || !liveData) return;
    const mergedEntries = watchlistEntries.map((entry) => {
      const liveItem = liveData.find(
        (ld) => ld.instrument_token === entry.instrument_token
      );
      if (liveItem) {
        return {
          ...entry,
          last_price: liveItem.last_price,
          change: liveItem.change,
          prevClose: liveItem?.ohlc?.close,
        };
      }
      return entry;
    });
    setWatchlistEntries(mergedEntries);
  }, [liveData]);

  // -------------------------------------------------------
  // Populate data for modals (like in Screener)
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
  // Listen for real-time watchlist update alerts from DataContext
  // -------------------------------------------------------
  useEffect(() => {
    if (watchlistAlerts) {
      // When watchlistAlerts changes, refetch watchlist names and entries.
      fetchWatchlistNames();
      if (selectedWatchlist) {
        handleSelectWatchlist(selectedWatchlist);
      }
    }
  }, [watchlistAlerts]);

  // -------------------------------------------------------
  // UI
  // -------------------------------------------------------
  return (
    <div
      className="mx-auto w-[95%] bg-[#1a1a1c] flex flex-col md:flex-row text-white relative"
      style={{ height: "calc(100vh - 96px)" }}
    >
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
      />
      <AddAlertModal
        isOpen={isAddAlertModalOpen}
        onClose={handleCloseAddAlertModal}
        symbol={addAlertData?.symbol}
        instrument_token={addAlertData?.instrument_token}
        ltp={addAlertData?.ltp}
      />
      {/* New Add Watchlist Modal */}
      <AddWatchlistModal
        isOpen={isAddWatchlistModalOpen}
        onClose={handleCloseAddWatchlistModal}
        onWatchlistAdded={fetchWatchlistNames}
      />

      {/* LEFT SIDEBAR: Search + Watchlist Entries */}
      <div
        className="relative flex flex-col 
          lg:w-3/12 md:w-5/12 sm:w-full 
          h-full p-4 border-b md:border-b-0 md:border-r bg-[#1a1a1c]"
      >
        {/* Search Bar Container */}
        <div
          ref={searchContainerRef}
          className="relative pb-2 mb-2 border-b border-zinc-600"
        >
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
            placeholder="Search"
            className="w-full h-10 pl-10 pr-2 rounded bg-[#1a1a1c] text-zinc-300 placeholder-zinc-600 focus:outline-none"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="absolute left-0 z-10 w-full mt-1 border rounded top-12 bg-[#1a1a1c] border-zinc-700">
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

        {/* Watchlist Entries */}
        <div className="flex-1 mt-2 space-y-1 overflow-auto">
          {isLoading && (
            <div className="flex items-center justify-center">
              <Spinner size="lg" />
            </div>
          )}
          {selectedWatchlist ? (
            watchlistEntries.length > 0 ? (
              watchlistEntries.map((entry) => {
                const colorClass =
                  entry.change > 0
                    ? "text-green-500"
                    : entry.change < 0
                    ? "text-red-500"
                    : "text-zinc-400";
                const priceDiff = entry.last_price - entry.prevClose || 0;
                const diffColor =
                  priceDiff > 0
                    ? "text-green-500"
                    : priceDiff < 0
                    ? "text-red-500"
                    : "text-zinc-400";
                return (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between px-2 py-3 border-b bg-[#1a1a1c] border-zinc-700 group"
                  >
                    <div className="text-sm">{entry.symbol}</div>
                    <div className="flex items-center gap-3">
                      <div className="block group-hover:hidden">
                        <span className={`text-xs ${diffColor} mr-1`}>
                          ({priceDiff.toFixed(2)})
                        </span>
                        <span className={`text-xs ${colorClass} mr-1`}>
                          {entry.change?.toFixed(2) || "0.00"}%
                        </span>
                        <span className={`text-sm ${colorClass}`}>
                          {entry.last_price?.toFixed(2) || "--"}
                        </span>
                      </div>
                      <div className="items-center hidden h-fit group-hover:flex">
                        <ButtonGroup className="h-6">
                          {userRole === "admin" && (
                            <>
                              <Button
                                isIconOnly
                                color="success"
                                variant="flat"
                                size="sm"
                                onPress={() => {
                                  populateBuyData(entry);
                                  handleOpenBuyModal();
                                }}
                              >
                                B
                              </Button>
                              <Button
                                isIconOnly
                                color="danger"
                                variant="flat"
                                size="sm"
                                onPress={() => {
                                  populateSellData(entry);
                                  handleOpenSellModal();
                                }}
                              >
                                S
                              </Button>
                              <Button
                                isIconOnly
                                color="primary"
                                variant="flat"
                                size="sm"
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
                                  className="size-4"
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
                            isIconOnly
                            color="warning"
                            variant="flat"
                            size="sm"
                            onPress={() => {
                              populateChartData(entry);
                              handleOpenChartModal();
                            }}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                              strokeWidth={1.5}
                              stroke="currentColor"
                              className="size-4"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                              />
                            </svg>
                          </Button>
                          <Button
                            isIconOnly
                            color="danger"
                            variant="flat"
                            size="sm"
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
                              className="size-4"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                              />
                            </svg>
                          </Button>
                        </ButtonGroup>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-zinc-400">No entries yet.</div>
            )
          ) : (
            <div className="text-zinc-400">No watchlist selected.</div>
          )}
        </div>
      </div>

      {/* RIGHT SIDE: Placeholder for future charts, etc. */}
      <div className="w-full h-full p-4 md:flex-1">
        <h2 className="mb-2 text-xl font-bold">Chart / Other Stuff</h2>
        <p className="text-zinc-400">
          This area can be used to display charts, analytics, or other content
          related to the selected stock/watchlist.
        </p>
      </div>

      {/* FOOTER */}
      <div className="static flex items-center justify-between w-full p-2 border-t md:absolute md:bottom-0 md:left-0 border-zinc-700 bg-zinc-800">
        <div className="ml-4 text-zinc-400">
          {selectedWatchlist
            ? `Watchlist: ${selectedWatchlist.name}`
            : "No watchlist selected"}
        </div>
        <div className="flex items-center gap-2 mr-4">
          {/* Dropdown of watchlists */}
          <select
            className="px-2 py-1 rounded bg-zinc-900 text-zinc-300 focus:outline-none"
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
          {/* Plus button to open Add Watchlist Modal */}
          <button
            className="px-3 py-1 text-white bg-blue-600 rounded"
            onClick={handleOpenAddWatchlistModal}
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
                d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
              />
            </svg>
          </button>
          {/* Delete button for watchlist (only for admin) */}
          {userRole === "admin" && selectedWatchlist && (
            <button
              className="px-3 py-1 text-white bg-red-600 rounded"
              onClick={handleDeleteWatchlist}
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Watchlist;
