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
  const screenOptions = ["VCP", "IPO"];
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
            className="bg-green-500 bg-opacity-90 hover:bg-green-600 text-white rounded-md px-4 py-2 min-w-[130px] sm:min-w-[150px]"
            onPress={fetchScreenerData}
          >
            Refresh Screener
          </Button>
          <select
            className="h-10 px-3 py-1 text-sm text-white transition-colors rounded bg-zinc-700 focus:outline-none hover:bg-zinc-600"
            style={{ minWidth: "80px" }}
            value={screen}
            onChange={(e) => setScreen(e.target.value)}
          >
            {screenOptions.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </div>
        {screenerData && (
          <span className="text-sm">Screen Count: {screenerData.length}</span>
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
              className="m-auto rounded-lg no-scrollbar bg-zinc-900"
              align="center"
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
                        <ButtonGroup>
                          {/* Buy */}
                          {userRole === "admin" && (
                            <>
                              <Button
                                isIconOnly
                                color="success"
                                variant="flat"
                                onPress={() => {
                                  populateBuyData(row);
                                  handleOpenBuyModal();
                                }}
                                isDisabled={userRole !== "admin"}
                              >
                                En
                              </Button>
                              {/* Sell */}
                              <Button
                                isIconOnly
                                color="danger"
                                variant="flat"
                                onPress={() => {
                                  populateSellData(row);
                                  handleOpenSellModal();
                                }}
                                isDisabled={userRole !== "admin"}
                              >
                                Ex
                              </Button>
                              <Button
                                isIconOnly
                                color="primary"
                                variant="flat"
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
                                  className="size-5"
                                  style={{ width: "24px", height: "24px" }}
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
                          {/* New: Add Alert Button (using second provided SVG) */}
                          {/* Chart */}
                          <Button
                            isIconOnly
                            color="warning"
                            variant="flat"
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
                              className="size-5"
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
          <div className="block space-y-4 md:hidden">
            {screenerData.map((row, idx) => {
              const colorClass =
                row.change > 0 ? "text-green-500" : "text-red-500";
              const atrPercent =
                ((row?.atr / row?.last_price) * 100).toFixed(2) + "%";
              return (
                <div
                  key={row.symbol}
                  className={`flex flex-col gap-2 p-3 bg-zinc-900 rounded-lg 
                              ${
                                idx < screenerData.length - 1
                                  ? "border-b border-zinc-700 rounded-none"
                                  : ""
                              }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-base font-semibold">
                      {row.symbol}
                    </span>
                    <ButtonGroup>
                      {/* Buy */}
                      {userRole === "admin" && (
                        <>
                          <Button
                            isIconOnly
                            color="success"
                            variant="flat"
                            onPress={() => {
                              populateBuyData(row);
                              handleOpenBuyModal();
                            }}
                            isDisabled={userRole !== "admin"}
                          >
                            En
                          </Button>
                          {/* Sell */}
                          <Button
                            isIconOnly
                            color="danger"
                            variant="flat"
                            onPress={() => {
                              populateSellData(row);
                              handleOpenSellModal();
                            }}
                            isDisabled={userRole !== "admin"}
                          >
                            Ex
                          </Button>
                          <Button
                            isIconOnly
                            color="primary"
                            variant="flat"
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
                              className="size-5"
                              style={{ width: "24px", height: "24px" }}
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
                      {/* New: Add Alert Button */}
                      {/* Chart */}
                      <Button
                        isIconOnly
                        color="warning"
                        variant="flat"
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
                          className="size-5"
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
                  <div className="flex flex-col gap-1 text-sm">
                    <div className="flex justify-between">
                      <span>Last Price:</span>
                      <span className={colorClass}>
                        {row.last_price?.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Change:</span>
                      <span className={colorClass}>
                        {row.change?.toFixed(2)} %
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>ATR %:</span>
                      <span>{atrPercent}</span>
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
