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
  DropdownSection,
  DropdownItem,
  Divider,
  Chip,
} from "@heroui/react";

import SellModal from "../components/SellModal";
import IncreaseModal from "../components/IncreaseModal";
import ReduceModal from "../components/ReduceModal";
import ModifySlModal from "../components/ModifySlModal";
import ModifyTgtModal from "../components/ModifyTgtModal";

function AllPositions() {
  const { liveData, positions, riskpool, historicalTrades } =
    useContext(DataContext);
  const [positionData, setPositionData] = React.useState(null);
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);
  const [isIncreaseModalOpen, setIncreaseModalOpen] = useState(false);
  const [isReduceModalOpen, setReduceModalOpen] = useState(false);
  const [isModifySlModalOpen, setModifySlModalOpen] = useState(false);
  const [isModifyTgtModalOpen, setModifyTgtModalOpen] = useState(false);
  const [totalPnl, setTotalPnl] = useState(0);
  const [capitalUsed, setCapitalUsed] = useState(0);

  const handleOpenSellModal = () => setIsSellModalOpen(true);
  const handleCloseSellModal = () => setIsSellModalOpen(false);

  const handleOpenIncreaseModal = () => setIncreaseModalOpen(true);
  const handleCloseIncreaseModal = () => setIncreaseModalOpen(false);

  const handleOpenReduceModal = () => setReduceModalOpen(true);
  const handleCloseReduceModal = () => setReduceModalOpen(false);

  const handleOpenModifySlModal = () => setModifySlModalOpen(true);
  const handleCloseModifySlModal = () => setModifySlModalOpen(false);

  const handleOpenModifyTgtModal = () => setModifyTgtModalOpen(true);
  const handleCloseModifyTgtModal = () => setModifyTgtModalOpen(false);

  useEffect(() => {
    if (positions?.data && liveData) {
      for (const data of positions?.data) {
        const liveDataItem = liveData.find(
          (item) => item.instrument_token === data.token
        );

        // Update 'change' only if 'liveDataItem' exists, otherwise keep the previous value
        if (liveDataItem) {
          data.last_price = liveDataItem?.last_price;
        }
      }
    }
  }, [liveData, positions]);

  const openChart = (symbol, instrument_token) => {
    window.open(
      `https://kite.zerodha.com/chart/ext/tvc/NSE/${symbol}/${instrument_token}?theme=dark`,
      "_blank"
    );
  };

  const populatePositionData = (row) => {
    setPositionData({
      booked_pnl: row.booked_pnl,
      current_qty: row.current_qty,
      entry_price: row.entry_price,
      entry_time: row.entry_time,
      initial_qty: row.initial_qty,
      stock_name: row.stock_name,
      stop_loss: row.stop_loss,
      target: row.target,
      token: row.token,
      last_price: row.last_price,
    });
  };

  useEffect(() => {
    if (positions?.data && liveData) {
      let totalPnl = 0;
      positions?.data.forEach((position) => {
        totalPnl +=
          (position.last_price - position.entry_price) * position.current_qty +
          position.booked_pnl;
      });
      setTotalPnl(totalPnl);
    }
    if (positions?.data) {
      let capitalUsed = 0;
      positions?.data.forEach((position) => {
        capitalUsed += position.entry_price * position.current_qty;
      });
      setCapitalUsed(capitalUsed);
    }
  }, [positionData, liveData]);

  return (
    <>
      {positions != null ? (
        <div className="px-6">
          <div className="flex items-center justify-between my-3">
            {positions != null ? (
              <span className="ml-2">
                {" "}
                Trades Count: {positions?.data?.length}
              </span>
            ) : null}
          </div>
          <Table
            aria-label="Example static collection table"
            className="m-auto overflow-y-scroll no-scrollbar"
            align="center"
          >
            <TableHeader>
              <TableColumn>Name</TableColumn>
              <TableColumn>Qty.</TableColumn>
              <TableColumn>Avg.</TableColumn>
              <TableColumn>Ltp</TableColumn>
              <TableColumn>Pnl</TableColumn>
              <TableColumn>Actions</TableColumn>
            </TableHeader>
            <TableBody>
              {positions?.data?.map((row) => (
                <TableRow key={row?.stock_name} className="hover:bg-zinc-800">
                  <TableCell>{row?.stock_name}</TableCell>
                  <TableCell>{row?.current_qty * 1}</TableCell>
                  <TableCell>{row?.entry_price?.toFixed(2)}</TableCell>
                  <TableCell>{row?.last_price?.toFixed(2)}</TableCell>
                  <TableCell
                    className={
                      (row?.last_price - row?.entry_price) * row?.current_qty +
                        row?.booked_pnl >
                      0
                        ? "text-green-500"
                        : "text-red-500"
                    }
                  >
                    {row.last_price
                      ? (
                          ((row?.last_price - row?.entry_price) *
                            row?.current_qty +
                            row?.booked_pnl) *
                          1
                        ).toFixed(2)
                      : 0}{" "}
                    (
                    {(
                      ((row?.last_price - row?.entry_price) /
                        row?.entry_price) *
                      100
                    ).toFixed(2)}
                    %)
                  </TableCell>
                  <TableCell>
                    <ButtonGroup>
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

                      <Button
                        isIconOnly
                        color="warning"
                        variant="flat"
                        target="_blank"
                        onPress={() => openChart(row.stock_name, row.token)}
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
                      <Dropdown className=" dark">
                        <DropdownTrigger>
                          <Button
                            isIconOnly
                            className="text-pink-300 bg-pink-400 bg-opacity-30"
                            variant="flat"
                            target="_blank"
                            onPress={() => openChart(row.stock_name, row.token)}
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
                          aria-label="Static Actions"
                          className="dark"
                        >
                          <DropdownItem
                            key="new"
                            className="p-0 hover:bg-zinc-900"
                          >
                            <div className="flex flex-col justify-between gap-1 p-3 text-left text-white rounded-lg w-72 bg-zinc-900">
                              <div className="text-xl">Stats</div>
                              <div className="py-1 text-md">
                                Stop-Loss: {row?.stop_loss?.toFixed(2)} (
                                {(
                                  ((row?.stop_loss - row?.entry_price) /
                                    row?.entry_price) *
                                  100
                                ).toFixed(2)}
                                %)
                                <button
                                  onClick={() => {
                                    populatePositionData(row);
                                    handleOpenModifySlModal();
                                  }}
                                  className="px-2 py-1 ml-2 text-xs bg-red-500 rounded-md bg-opacity-40 hover:bg-red-700"
                                >
                                  C
                                </button>
                              </div>
                              <div className="py-1 text-md">
                                Target: {row?.target?.toFixed(2)} (
                                {(
                                  ((row?.target - row?.entry_price) /
                                    row?.entry_price) *
                                  100
                                ).toFixed(2)}
                                %)
                                <button
                                  onClick={() => {
                                    populatePositionData(row);
                                    handleOpenModifyTgtModal();
                                  }}
                                  className="px-2 py-1 ml-2 text-xs bg-green-500 rounded-md bg-opacity-40 hover:bg-green-700"
                                >
                                  C
                                </button>
                              </div>
                              <div className="py-1 text-white text-md">
                                Capital Used:{" "}
                                {(
                                  row?.entry_price *
                                  row?.current_qty *
                                  1
                                ).toFixed(2)}
                              </div>
                              <div className="py-1 text-md">
                                Risk:{" "}
                                {(
                                  (row?.stop_loss - row?.entry_price) *
                                    row?.current_qty *
                                    1 +
                                  row?.booked_pnl * 1
                                ).toFixed(2)}
                              </div>
                              <div className="py-1 text-md">
                                Reward:{" "}
                                {(
                                  (row?.target - row?.entry_price) *
                                    row?.current_qty *
                                    1 +
                                  row?.booked_pnl * 1
                                ).toFixed(2)}
                              </div>
                              <div
                                className={
                                  row?.booked_pnl > 0
                                    ? "text-green-500 text-md py-1"
                                    : "text-red-500 text-md py-1"
                                }
                              >
                                Booked: {(row?.booked_pnl * 1)?.toFixed(2)}
                              </div>
                            </div>
                          </DropdownItem>
                        </DropdownMenu>
                      </Dropdown>
                    </ButtonGroup>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex flex-wrap justify-between w-full gap-4 mt-3">
            <div className="flex flex-col justify-between gap-1 p-5 text-left rounded-lg shadow-lg min-w-64 max-w-72 bg-zinc-800">
              <span>Total P&L</span>
              <span
                className={
                  totalPnl > 0
                    ? "text-green-500 text-2xl mt-3 flex items-end gap-1"
                    : "text-red-500 text-2xl mt-3 flex items-end gap-1"
                }
              >
                {(totalPnl * 1)?.toFixed(2)}{" "}
                <span className="text-medium">
                  ({((totalPnl / capitalUsed) * 100).toFixed(2)}%)
                </span>
              </span>
            </div>
            <div className="flex flex-col justify-between gap-1 p-5 text-left rounded-lg shadow-lg min-w-64 max-w-72 bg-zinc-800">
              <span>Capital Used</span>
              <span className="mt-3 text-2xl">
                {(capitalUsed * 1)?.toFixed(2)}
              </span>
            </div>
            <div className="flex flex-col justify-between gap-1 p-5 text-left rounded-lg shadow-lg min-w-64 max-w-72 bg-zinc-800">
              <span>Used Risk</span>
              <span className="mt-3 text-2xl">
                {(riskpool?.data?.used_risk * 1)?.toFixed(2)}
              </span>
            </div>
            <div className="flex flex-col justify-between gap-1 p-5 text-left rounded-lg shadow-lg min-w-64 max-w-72 bg-zinc-800">
              <span>Available Risk</span>
              <span className="mt-3 text-2xl">
                {(riskpool?.data?.available_risk * 1)?.toFixed(2)}
              </span>
            </div>
            <div className="flex flex-col justify-between gap-1 p-5 text-left rounded-lg shadow-lg min-w-64 max-w-72 bg-zinc-800">
              <span>Total Risk</span>
              <span className="mt-3 text-2xl">
                {(
                  (riskpool?.data?.available_risk + riskpool?.data?.used_risk) *
                  1
                ).toFixed(2)}
              </span>
            </div>
          </div>
          <IncreaseModal
            isOpen={isIncreaseModalOpen}
            onClose={handleCloseIncreaseModal}
            symbol={positionData?.stock_name}
            ltp={positionData?.last_price}
            AvailableRisk={riskpool?.data?.available_risk}
            UsedRisk={riskpool?.data?.used_risk}
          />

          <ReduceModal
            isOpen={isReduceModalOpen}
            onClose={handleCloseReduceModal}
            symbol={positionData?.stock_name}
            ltp={positionData?.last_price}
            AvailableRisk={riskpool?.data?.available_risk}
            UsedRisk={riskpool?.data?.used_risk}
            currentQuantity={positionData?.current_qty}
          />

          <SellModal
            isOpen={isSellModalOpen}
            onClose={handleCloseSellModal}
            AvailableRisk={riskpool?.data?.available_risk}
            UsedRisk={riskpool?.data?.used_risk}
            symbol={positionData?.stock_name}
          />

          <ModifySlModal
            isOpen={isModifySlModalOpen}
            onClose={handleCloseModifySlModal}
            AvailableRisk={riskpool?.data?.available_risk}
            UsedRisk={riskpool?.data?.used_risk}
            symbol={positionData?.stock_name}
            currentEntryPrice={positionData?.entry_price}
          />

          <ModifyTgtModal
            isOpen={isModifyTgtModalOpen}
            onClose={handleCloseModifyTgtModal}
            AvailableRisk={riskpool?.data?.available_risk}
            UsedRisk={riskpool?.data?.used_risk}
            symbol={positionData?.stock_name}
            currentEntryPrice={positionData?.entry_price}
          />
        </div>
      ) : (
        <div className="flex flex-col justify-center items-center w-full h-[85vh]">
          <Spinner size="lg" />
          <span className="m-5 text-2xl">Loading Positions Data</span>
        </div>
      )}
    </>
  );
}

export default AllPositions;
