import React, { useEffect, useContext, useState } from "react";
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
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
} from "@heroui/react";

import SellModal from "../components/SellModal";
import IncreaseModal from "../components/IncreaseModal";
import ReduceModal from "../components/ReduceModal";
import ModifySlModal from "../components/ModifySlModal";
import ModifyTgtModal from "../components/ModifyTgtModal";
import ChartModal from "../components/ChartModal";
import AddAlertModal from "../components/AddAlertModal"; // New import for Add Alert modal
import { AuthContext } from "../utils/AuthContext";
import { jwtDecode } from "jwt-decode"; // ✅ Correct import
import api from "../utils/api"; // Adjust the path as necessary
import { toast } from "sonner";
import { PlayToastSound } from "../utils/PlaySound";

function AllPositions() {
  const { liveData, positions, riskpool } = useContext(DataContext);
  const { token, logout } = useContext(AuthContext);

  // For storing row data when opening modals
  const [positionData, setPositionData] = useState(null);
  const [chartData, setChartData] = useState(null);
  // New state for Add Alert modal
  const [addAlertData, setAddAlertData] = useState(null);

  // Modal states
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);
  const [isIncreaseModalOpen, setIsIncreaseModalOpen] = useState(false);
  const [isReduceModalOpen, setIsReduceModalOpen] = useState(false);
  const [isModifySlModalOpen, setIsModifySlModalOpen] = useState(false);
  const [isModifyTgtModalOpen, setIsModifyTgtModalOpen] = useState(false);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [isAddAlertModalOpen, setIsAddAlertModalOpen] = useState(false);
  // Stats
  const [totalPnl, setTotalPnl] = useState(0);
  const [capitalUsed, setCapitalUsed] = useState(0);

  let multiplier = 1;
  let userRole = "";
  if (token) {
    try {
      const decoded = jwtDecode(token); // ✅ Use named import
      userRole = decoded.role || "";
      if (userRole !== "admin") {
        multiplier = 25;
      }
    } catch (error) {
      console.error("Failed to decode token:", error);
    }
  }

  // Merge live data into positions for last_price
  useEffect(() => {
    if (positions && liveData) {
      positions.forEach((pos) => {
        const item = liveData.find(
          (liveItem) => liveItem.instrument_token === pos.token
        );
        if (item) {
          pos.last_price = item.last_price;
        }
      });
    }
  }, [positions, liveData]);

  // Recompute total P&L and capital used
  useEffect(() => {
    if (positions) {
      let runningPnl = 0;
      let runningCap = 0;
      positions.forEach((pos) => {
        const currentVal = pos.last_price * pos.current_qty + pos.booked_pnl;
        runningPnl +=
          (pos.last_price - pos.entry_price) * pos.current_qty + pos.booked_pnl;
        runningCap += pos.entry_price * pos.current_qty;
      });
      setTotalPnl(runningPnl);
      setCapitalUsed(runningCap);
    }
  }, [positions, liveData]);

  // For row-based modals
  const populatePositionData = (row) => setPositionData({ ...row });
  const populateChartData = (row) => {
    setChartData({
      symbol: row.stock_name,
      token: row.token,
    });
  };
  // New: Populate data for Add Alert modal from a position row.
  const populateAddAlertData = (row) => {
    setAddAlertData({
      stock_name: row.stock_name, // Use stock_name as symbol
      token: row.token, // instrument token
      last_price: row.last_price,
    });
  };

  // Modal Handlers
  const handleOpenSellModal = () => setIsSellModalOpen(true);
  const handleCloseSellModal = () => setIsSellModalOpen(false);

  const handleOpenIncreaseModal = () => setIsIncreaseModalOpen(true);
  const handleCloseIncreaseModal = () => setIsIncreaseModalOpen(false);

  const handleOpenReduceModal = () => setIsReduceModalOpen(true);
  const handleCloseReduceModal = () => setIsReduceModalOpen(false);

  const handleOpenModifySlModal = () => setIsModifySlModalOpen(true);
  const handleCloseModifySlModal = () => setIsModifySlModalOpen(false);

  const handleOpenModifyTgtModal = () => setIsModifyTgtModalOpen(true);
  const handleCloseModifyTgtModal = () => setIsModifyTgtModalOpen(false);

  const handleOpenChartModal = () => setIsChartModalOpen(true);
  const handleCloseChartModal = () => setIsChartModalOpen(false);

  const handleOpenAddAlertModal = () => setIsAddAlertModalOpen(true);
  const handleCloseAddAlertModal = () => setIsAddAlertModalOpen(false);

  const toggleAutoExit = async (row) => {
    try {
      const newValue = !row.auto_exit;
      const response = await api.get(
        `/api/order/toggle_auto_exit?trade_id=${row.trade_id}&auto_exit=${newValue}`
      );
      if (response.data.status === "success") {
        PlayToastSound();
        toast.success("Auto exit toggled", {
          duration: 5000,
        });
      } else {
        console.log("Failed to toggle auto exit flag");
      }
    } catch (error) {
      console.log("Error toggling auto exit flag", error);
    }
  };

  if (!positions) {
    return (
      <div className="flex flex-col justify-center items-center w-full h-[85vh]">
        <Spinner size="lg" />
        <span className="m-5 text-2xl">Loading Positions Data</span>
      </div>
    );
  }

  return (
    <>
      <div className="w-full px-6">
        {/* TOP STATS */}
        <div className="flex flex-wrap justify-between gap-1 my-3">
          <div className="flex flex-col bg-zinc-900 rounded-lg p-3 max-w-[120px] md:max-w-[250px]">
            <span className="text-sm text-zinc-400">Total P&L</span>
            <span
              className={`text-xl mt-1 ${
                totalPnl >= 0 ? "text-green-400" : "text-red-400"
              }`}
            >
              {(totalPnl * multiplier).toFixed(2)}{" "}
              <span className="ml-2 text-sm text-zinc-400">
                (
                {capitalUsed === 0
                  ? "0.00"
                  : ((totalPnl / capitalUsed) * 100).toFixed(2)}
                %)
              </span>
            </span>
          </div>
          <div className="flex flex-col bg-zinc-900 rounded-lg p-3 max-w-[120px] md:max-w-[250px]">
            <span className="text-sm text-zinc-400">Capital Used</span>
            <span className="mt-1 text-xl text-zinc-200">
              {(capitalUsed * multiplier).toFixed(2)}
            </span>
          </div>
          <div className="flex flex-col bg-zinc-900 rounded-lg p-3 max-w-[120px] md:max-w-[250px]">
            <span className="text-sm text-zinc-400">Used Risk</span>
            <span className="mt-1 text-xl text-zinc-200">
              {(riskpool?.used_risk * multiplier || 0).toFixed(2)}
            </span>
          </div>
          <div className="flex flex-col bg-zinc-900 rounded-lg p-3 max-w-[120px] md:max-w-[250px]">
            <span className="text-sm text-zinc-400">Available Risk</span>
            <span className="mt-1 text-xl text-zinc-200">
              {(riskpool?.available_risk * multiplier || 0).toFixed(2)}
            </span>
          </div>
          <div className="flex flex-col bg-zinc-900 rounded-lg p-3 max-w-[120px] md:max-w-[250px]">
            <span className="text-sm text-zinc-400">Total Risk</span>
            <span className="mt-1 text-xl text-zinc-200">
              {(
                (riskpool?.available_risk * multiplier || 0) +
                (riskpool?.used_risk * multiplier || 0)
              ).toFixed(2)}
            </span>
          </div>
        </div>

        {/* DESKTOP TABLE */}
        <div className="hidden w-full md:block">
          <Table
            aria-label="Positions Table"
            className="w-full table-auto no-scrollbar"
            align="center"
          >
            <TableHeader>
              <TableColumn>Instrument</TableColumn>
              <TableColumn>Qty</TableColumn>
              <TableColumn>Avg Cost</TableColumn>
              <TableColumn>LTP</TableColumn>
              <TableColumn>Cur. Val</TableColumn>
              <TableColumn>P&L</TableColumn>
              <TableColumn>Actions</TableColumn>
            </TableHeader>
            <TableBody>
              {positions.map((row) => {
                const curVal =
                  row.last_price * row.current_qty + row.booked_pnl;
                const currentPnl =
                  (row.last_price - row.entry_price) * row.current_qty +
                  row.booked_pnl;
                const pnlClass =
                  currentPnl > 0 ? "text-green-500" : "text-red-500";
                const pnlPercent = (
                  ((row.last_price - row.entry_price) / row.entry_price) *
                  100
                ).toFixed(2);
                return (
                  <TableRow key={row.stock_name} className="hover:bg-zinc-800">
                    <TableCell>{row.stock_name}</TableCell>
                    <TableCell>
                      {(row.current_qty * multiplier).toFixed(2)}
                    </TableCell>
                    <TableCell>{row.entry_price?.toFixed(2)}</TableCell>
                    <TableCell>{row.last_price?.toFixed(2)}</TableCell>
                    <TableCell>{(curVal * multiplier).toFixed(2)}</TableCell>
                    <TableCell className={pnlClass}>
                      {(currentPnl * multiplier).toFixed(2)} ({pnlPercent}%)
                    </TableCell>
                    <TableCell>
                      <ButtonGroup>
                        {userRole === "admin" && (
                          <>
                            <Button
                              isIconOnly
                              color="success"
                              variant="flat"
                              onPress={() => {
                                populatePositionData(row);
                                handleOpenIncreaseModal();
                              }}
                            >
                              In
                            </Button>
                            <Button
                              isIconOnly
                              color="secondary"
                              variant="flat"
                              onPress={() => {
                                populatePositionData(row);
                                handleOpenReduceModal();
                              }}
                            >
                              Re
                            </Button>
                            <Button
                              isIconOnly
                              color="danger"
                              variant="flat"
                              onPress={() => {
                                populatePositionData(row);
                                handleOpenSellModal();
                              }}
                            >
                              Ex
                            </Button>
                            {/* New: Add Alert Button */}
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
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0M3.124 7.5A8.969 8.969 0 0 1 5.292 3m13.416 0a8.969 8.969 0 0 1 2.168 4.5"
                                />
                              </svg>
                            </Button>

                            {/* Stats dropdown */}
                            <Dropdown className="dark">
                              <DropdownTrigger>
                                <Button
                                  isIconOnly
                                  className="text-pink-300 bg-pink-400 bg-opacity-30"
                                  variant="flat"
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
                                      d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
                                    />
                                  </svg>
                                </Button>
                              </DropdownTrigger>
                              <DropdownMenu
                                aria-label="Stats Menu"
                                className="dark"
                              >
                                <DropdownItem
                                  className="p-0 hover:bg-zinc-900"
                                  textValue="Stats"
                                >
                                  <div className="flex flex-col justify-between gap-1 p-3 text-left text-white rounded-lg w-72 bg-zinc-900">
                                    <div className="text-xl">Stats</div>
                                    <div className="py-1 text-md">
                                      Stop-Loss: {row.stop_loss?.toFixed(2)} (
                                      {(
                                        ((row.stop_loss - row.entry_price) /
                                          row.entry_price) *
                                        100
                                      ).toFixed(2)}
                                      %)
                                      {userRole === "admin" && (
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            populatePositionData(row);
                                            handleOpenModifySlModal();
                                          }}
                                          disabled={userRole !== "admin"}
                                          className="px-2 py-1 ml-2 text-xs bg-red-500 rounded-md bg-opacity-40 hover:bg-red-700"
                                        >
                                          C
                                        </button>
                                      )}
                                    </div>
                                    <div className="py-1 text-md">
                                      Target: {row.target?.toFixed(2)} (
                                      {(
                                        ((row.target - row.entry_price) /
                                          row.entry_price) *
                                        100
                                      ).toFixed(2)}
                                      %)
                                      {userRole === "admin" && (
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            populatePositionData(row);
                                            handleOpenModifyTgtModal();
                                          }}
                                          disabled={userRole !== "admin"}
                                          className="px-2 py-1 ml-2 text-xs bg-green-500 rounded-md bg-opacity-40 hover:bg-green-700"
                                        >
                                          C
                                        </button>
                                      )}
                                    </div>
                                    <div className="py-1 text-md">
                                      Capital Used:{" "}
                                      {(
                                        row.entry_price *
                                        row.current_qty *
                                        multiplier
                                      ).toFixed(2)}
                                    </div>
                                    <div className="py-1 text-md">
                                      Risk:{" "}
                                      {(
                                        ((row.stop_loss - row.entry_price) *
                                          row.current_qty +
                                          row.booked_pnl) *
                                        multiplier
                                      ).toFixed(2)}
                                    </div>
                                    <div className="py-1 text-md">
                                      Reward:{" "}
                                      {(
                                        ((row.target - row.entry_price) *
                                          row.current_qty +
                                          row.booked_pnl) *
                                        multiplier
                                      ).toFixed(2)}
                                    </div>
                                    <div
                                      className={
                                        row.booked_pnl > 0
                                          ? "text-green-500 text-md py-1"
                                          : "text-red-500 text-md py-1"
                                      }
                                    >
                                      Booked:{" "}
                                      {(row.booked_pnl * multiplier).toFixed(2)}
                                    </div>
                                    {userRole === "admin" && (
                                      <div className="py-1">
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            toggleAutoExit(row);
                                          }}
                                          className="px-2 py-1 text-xs bg-blue-500 rounded-md bg-opacity-40 hover:bg-blue-700"
                                        >
                                          {`Auto Exit: ${
                                            row.auto_exit ? "True" : "False"
                                          }`}
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </DropdownItem>
                              </DropdownMenu>
                            </Dropdown>
                          </>
                        )}
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

        {/* MOBILE CARD LAYOUT */}
        <div className="block mt-3 space-y-3 md:hidden">
          {positions.map((row, idx) => {
            const curVal = row.last_price * row.current_qty + row.booked_pnl;
            const currentPnl =
              (row.last_price - row.entry_price) * row.current_qty +
              row.booked_pnl;
            const pnlClass = currentPnl > 0 ? "text-green-500" : "text-red-500";
            const pnlPercent = (
              ((row.last_price - row.entry_price) / row.entry_price) *
              100
            ).toFixed(2);
            return (
              <div
                key={row.stock_name}
                className={`flex flex-col gap-2 p-3 bg-zinc-900 rounded-lg 
                            ${
                              idx < positions.length - 1
                                ? "border-b border-zinc-700 rounded-none"
                                : ""
                            }`}
              >
                {/* Title row with Instrument name and Actions */}
                <div className="flex items-center justify-between">
                  <span className="text-base font-semibold">
                    {row.stock_name}
                  </span>
                  <ButtonGroup>
                    {userRole === "admin" && (
                      <>
                        <Button
                          isIconOnly
                          color="success"
                          variant="flat"
                          onPress={() => {
                            populatePositionData(row);
                            handleOpenIncreaseModal();
                          }}
                        >
                          In
                        </Button>
                        <Button
                          isIconOnly
                          color="secondary"
                          variant="flat"
                          onPress={() => {
                            populatePositionData(row);
                            handleOpenReduceModal();
                          }}
                        >
                          Re
                        </Button>
                        <Button
                          isIconOnly
                          color="danger"
                          variant="flat"
                          onPress={() => {
                            populatePositionData(row);
                            handleOpenSellModal();
                          }}
                        >
                          Ex
                        </Button>
                        {/* New: Add Alert Button */}
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
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0M3.124 7.5A8.969 8.969 0 0 1 5.292 3m13.416 0a8.969 8.969 0 0 1 2.168 4.5"
                            />
                          </svg>
                        </Button>
                        <Dropdown className="dark">
                          <DropdownTrigger>
                            <Button
                              isIconOnly
                              className="text-pink-300 bg-pink-400 bg-opacity-30"
                              variant="flat"
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
                                  d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
                                />
                              </svg>
                            </Button>
                          </DropdownTrigger>
                          <DropdownMenu
                            aria-label="Stats Menu"
                            className="dark"
                          >
                            <DropdownItem
                              className="p-0 hover:bg-zinc-900"
                              textValue="Stats"
                            >
                              <div className="flex flex-col justify-between gap-1 p-3 text-left text-white rounded-lg w-72 bg-zinc-900">
                                <div className="text-xl">Stats</div>
                                <div className="py-1 text-md">
                                  Stop-Loss: {row.stop_loss?.toFixed(2)} (
                                  {(
                                    ((row.stop_loss - row.entry_price) /
                                      row.entry_price) *
                                    100
                                  ).toFixed(2)}
                                  %)
                                  {userRole === "admin" && (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        populatePositionData(row);
                                        handleOpenModifySlModal();
                                      }}
                                      disabled={userRole !== "admin"}
                                      className="px-2 py-1 ml-2 text-xs bg-red-500 rounded-md bg-opacity-40 hover:bg-red-700"
                                    >
                                      C
                                    </button>
                                  )}
                                </div>
                                <div className="py-1 text-md">
                                  Target: {row.target?.toFixed(2)} (
                                  {(
                                    ((row.target - row.entry_price) /
                                      row.entry_price) *
                                    100
                                  ).toFixed(2)}
                                  %)
                                  {userRole === "admin" && (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        populatePositionData(row);
                                        handleOpenModifyTgtModal();
                                      }}
                                      disabled={userRole !== "admin"}
                                      className="px-2 py-1 ml-2 text-xs bg-green-500 rounded-md bg-opacity-40 hover:bg-green-700"
                                    >
                                      C
                                    </button>
                                  )}
                                </div>
                                <div className="py-1 text-md">
                                  Capital Used:{" "}
                                  {(
                                    row.entry_price *
                                    row.current_qty *
                                    multiplier
                                  ).toFixed(2)}
                                </div>
                                <div className="py-1 text-md">
                                  Risk:{" "}
                                  {(
                                    ((row.stop_loss - row.entry_price) *
                                      row.current_qty +
                                      row.booked_pnl) *
                                    multiplier
                                  ).toFixed(2)}
                                </div>
                                <div className="py-1 text-md">
                                  Reward:{" "}
                                  {(
                                    ((row.target - row.entry_price) *
                                      row.current_qty +
                                      row.booked_pnl) *
                                    multiplier
                                  ).toFixed(2)}
                                </div>
                                <div
                                  className={
                                    row.booked_pnl > 0
                                      ? "text-green-500 text-md py-1"
                                      : "text-red-500 text-md py-1"
                                  }
                                >
                                  Booked:{" "}
                                  {(row.booked_pnl * multiplier).toFixed(2)}
                                </div>
                                {userRole === "admin" && (
                                  <div className="py-1">
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        toggleAutoExit(row);
                                      }}
                                      className="px-2 py-1 text-xs bg-blue-500 rounded-md bg-opacity-40 hover:bg-blue-700"
                                    >
                                      {`Auto Exit: ${
                                        row.auto_exit ? "True" : "False"
                                      }`}
                                    </button>
                                  </div>
                                )}
                              </div>
                            </DropdownItem>
                          </DropdownMenu>
                        </Dropdown>
                      </>
                    )}
                    {/* Chart Button */}
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
                {/* Body of the card with details */}
                <div className="flex flex-col gap-1 mt-2 text-sm">
                  <div className="flex justify-between">
                    <span>Qty</span>
                    <span>{(row.current_qty * multiplier).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg Cost</span>
                    <span>{row.entry_price?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>LTP</span>
                    <span>{row.last_price?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cur. Val</span>
                    <span>{(curVal * multiplier).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>P&L</span>
                    <span className={pnlClass}>
                      {(currentPnl * multiplier).toFixed(2)} ({pnlPercent}%)
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Modals */}
        <SellModal
          isOpen={isSellModalOpen}
          onClose={handleCloseSellModal}
          symbol={positionData?.stock_name}
          AvailableRisk={riskpool?.available_risk}
          UsedRisk={riskpool?.used_risk}
        />
        <IncreaseModal
          isOpen={isIncreaseModalOpen}
          onClose={handleCloseIncreaseModal}
          symbol={positionData?.stock_name}
          ltp={positionData?.last_price}
          AvailableRisk={riskpool?.available_risk}
          UsedRisk={riskpool?.used_risk}
        />
        <ReduceModal
          isOpen={isReduceModalOpen}
          onClose={handleCloseReduceModal}
          symbol={positionData?.stock_name}
          ltp={positionData?.last_price}
          AvailableRisk={riskpool?.available_risk}
          UsedRisk={riskpool?.used_risk}
          currentQuantity={positionData?.current_qty}
        />
        <ModifySlModal
          isOpen={isModifySlModalOpen}
          onClose={handleCloseModifySlModal}
          symbol={positionData?.stock_name}
          currentEntryPrice={positionData?.entry_price}
          AvailableRisk={riskpool?.available_risk}
          UsedRisk={riskpool?.used_risk}
        />
        <ModifyTgtModal
          isOpen={isModifyTgtModalOpen}
          onClose={handleCloseModifyTgtModal}
          symbol={positionData?.stock_name}
          currentEntryPrice={positionData?.entry_price}
          AvailableRisk={riskpool?.available_risk}
          UsedRisk={riskpool?.used_risk}
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
          symbol={addAlertData?.stock_name}
          instrument_token={addAlertData?.token}
          ltp={addAlertData?.last_price}
        />
      </div>
    </>
  );
}

export default AllPositions;
