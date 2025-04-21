// Screener.jsx
import React, { useState, useEffect, useContext } from "react";
import { DataContext } from "../utils/DataContext";
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
  ButtonGroup,
  Spinner,
} from "@heroui/react";
import BuyModal from "../components/BuyModal";
import SellModal from "../components/SellModal";
import ChartModal from "../components/ChartModal";
import AddAlertModal from "../components/AddAlertModal"; // New modal for adding alert
import api from "../utils/api";
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode"; // ✅ Correct import

function Screener() {
  const { liveData, riskpool } = useContext(DataContext);
  const { token, logout } = useContext(AuthContext);
  const screenOptions = ["VCP", "Weekly VCP", "IPO"];
  const [screenerData, setScreenerData] = useState(null);
  const [screen, setScreen] = useState("VCP");

  // Modals for buy, sell, chart and now add alert
  const [isBuyModalOpen, setIsBuyModalOpen] = useState(false);
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [isAddAlertModalOpen, setIsAddAlertModalOpen] = useState(false);

  // Data for modals
  const [buyData, setBuyData] = useState(null);
  const [sellData, setSellData] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [addAlertData, setAddAlertData] = useState(null);

  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token); // ✅ Use named import
      userRole = decoded.role || "";
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }
  // Fetch screener data
  const fetchScreenerData = async () => {
    setScreenerData(null);
    if (screen === "VCP") {
      const response = await api.get("/api/screener/vcpscreen");
      setScreenerData(response?.data);
    } else if (screen === "Weekly VCP") {
      const response = await api.get("/api/screener/weekly_vcpscreen");
      setScreenerData(response?.data);
    } else if (screen === "IPO") {
      const response = await api.get("/api/screener/iposcreen");
      setScreenerData(response?.data);
    }
  };

  useEffect(() => {
    fetchScreenerData();
  }, [screen]);

  // Merge liveData into screenerData
  useEffect(() => {
    if (!screenerData || !liveData) return;
    let changed = false;
    const newData = screenerData.map((item) => {
      const liveDataItem = liveData.find(
        (liveItem) => liveItem.instrument_token === item.instrument_token
      );
      if (liveDataItem) {
        const updatedItem = { ...item };
        if (updatedItem.change !== liveDataItem.change) {
          updatedItem.change = liveDataItem.change;
          changed = true;
        }
        if (updatedItem.last_price !== liveDataItem.last_price) {
          updatedItem.last_price = liveDataItem.last_price;
          changed = true;
        }
        return updatedItem;
      }
      return item;
    });
    newData.sort((a, b) => (b.change || 0) - (a.change || 0));
    const oldString = JSON.stringify(screenerData);
    const newString = JSON.stringify(newData);
    if (oldString !== newString) {
      setScreenerData(newData);
    }
  }, [liveData, screenerData]);

  // Populate data for modals
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

  // Modal Handlers
  const handleOpenBuyModal = () => setIsBuyModalOpen(true);
  const handleCloseBuyModal = () => setIsBuyModalOpen(false);

  const handleOpenSellModal = () => setIsSellModalOpen(true);
  const handleCloseSellModal = () => setIsSellModalOpen(false);

  const handleOpenChartModal = () => setIsChartModalOpen(true);
  const handleCloseChartModal = () => setIsChartModalOpen(false);

  const handleOpenAddAlertModal = () => setIsAddAlertModalOpen(true);
  const handleCloseAddAlertModal = () => setIsAddAlertModalOpen(false);

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
      />
      <AddAlertModal
        isOpen={isAddAlertModalOpen}
        onClose={handleCloseAddAlertModal}
        symbol={addAlertData?.symbol}
        instrument_token={addAlertData?.instrument_token}
        ltp={addAlertData?.ltp}
      />

      {/* Top controls */}
      <div className="flex flex-col items-center justify-between my-3 sm:flex-row">
        <div className="flex items-center gap-3">
          <Button
            size="md"
            color="success"
            variant="flat"
            className="min-w-[150px] h-10 px-4 bg-green-500/20 hover:bg-green-500/30 text-green-500"
            onPress={fetchScreenerData}
          >
            Refresh Screener
          </Button>
          <select
            className="h-10 px-4 py-1 text-sm text-white rounded-md border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 focus:outline-none focus:ring-2 focus:ring-green-500 shadow-md"
            value={screen}
            onChange={(e) => setScreen(e.target.value)}
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
                <TableColumn>Last Price</TableColumn>
                <TableColumn>Change</TableColumn>
                <TableColumn>ATR %</TableColumn>
                <TableColumn>Actions</TableColumn>
              </TableHeader>
              <TableBody>
                {screenerData?.map((row) => {
                  const colorClass =
                    row.change > 0 ? "text-green-500" : "text-red-500";
                  const atrPercent =
                    ((row?.atr / row?.last_price) * 100).toFixed(2) + "%";
                  return (
                    <TableRow
                      key={row.symbol}
                      className="cursor-pointer hover:bg-zinc-800"
                    >
                      <TableCell>{row.symbol}</TableCell>
                      <TableCell className={colorClass}>
                        {row.last_price?.toFixed(2)}
                      </TableCell>
                      <TableCell className={colorClass}>
                        {row.change?.toFixed(2)} %
                      </TableCell>
                      <TableCell>{atrPercent}</TableCell>
                      <TableCell>
                        <ButtonGroup className="shadow-sm">
                          {userRole === "admin" && (
                            <>
                              <Button
                                size="sm"
                                color="success"
                                variant="flat"
                                className="min-w-[40px] h-9 px-3 bg-green-500/20 hover:bg-green-500/30 text-green-500"
                                onPress={() => {
                                  populateBuyData(row);
                                  handleOpenBuyModal();
                                }}
                                isDisabled={userRole !== "admin"}
                              >
                                En
                              </Button>
                              <Button
                                size="sm"
                                color="danger"
                                variant="flat"
                                className="min-w-[40px] h-9 px-3 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                                onPress={() => {
                                  populateSellData(row);
                                  handleOpenSellModal();
                                }}
                                isDisabled={userRole !== "admin"}
                              >
                                Ex
                              </Button>
                              <Button
                                size="sm"
                                color="primary"
                                variant="flat"
                                className="min-w-[40px] h-9 bg-blue-500/20 hover:bg-blue-500/30 text-blue-500"
                                onPress={() => {
                                  populateAddAlertData(row);
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
                              populateChartData(row);
                              handleOpenChartModal();
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
                        </ButtonGroup>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          {/* Mobile Card Layout */}
          <div className="block mt-4 space-y-4 md:hidden">
            {screenerData.map((row, idx) => {
              const colorClass =
                row.change > 0 ? "text-green-500" : "text-red-500";
              const atrPercent =
                ((row?.atr / row?.last_price) * 100).toFixed(2) + "%";
              return (
                <div
                  key={row.symbol}
                  className="flex flex-col gap-3 p-4 bg-zinc-900 rounded-xl border border-zinc-800 shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-base font-semibold">
                      {row.symbol}
                    </span>
                    <ButtonGroup className="shadow-sm">
                      {userRole === "admin" && (
                        <>
                          <Button
                            size="sm"
                            color="success"
                            variant="flat"
                            className="min-w-[40px] h-9 px-3 bg-green-500/20 hover:bg-green-500/30 text-green-500"
                            onPress={() => {
                              populateBuyData(row);
                              handleOpenBuyModal();
                            }}
                            isDisabled={userRole !== "admin"}
                          >
                            En
                          </Button>
                          <Button
                            size="sm"
                            color="danger"
                            variant="flat"
                            className="min-w-[40px] h-9 px-3 bg-red-500/20 hover:bg-red-500/30 text-red-500"
                            onPress={() => {
                              populateSellData(row);
                              handleOpenSellModal();
                            }}
                            isDisabled={userRole !== "admin"}
                          >
                            Ex
                          </Button>
                          <Button
                            size="sm"
                            color="primary"
                            variant="flat"
                            className="min-w-[40px] h-9 bg-blue-500/20 hover:bg-blue-500/30 text-blue-500"
                            onPress={() => {
                              populateAddAlertData(row);
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
                          populateChartData(row);
                          handleOpenChartModal();
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
                    </ButtonGroup>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-1">
                    <div className="flex flex-col">
                      <span className="text-xs text-zinc-400 font-medium">
                        Last Price
                      </span>
                      <span className={`text-sm font-medium ${colorClass}`}>
                        {row.last_price?.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs text-zinc-400 font-medium">
                        Change
                      </span>
                      <span className={`text-sm font-medium ${colorClass}`}>
                        {row.change?.toFixed(2)} %
                      </span>
                    </div>
                    <div className="flex flex-col col-span-2">
                      <span className="text-xs text-zinc-400 font-medium">
                        ATR %
                      </span>
                      <span className="text-sm font-medium">{atrPercent}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

export default Screener;
