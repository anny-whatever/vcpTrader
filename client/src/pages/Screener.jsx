import React from "react";
import { DataContext } from "../utils/DataContext";
import { useState, useEffect, useContext } from "react";
import {
  Table,
  TableHeader,
  TableBody,
  TableColumn,
  TableRow,
  TableCell,
  Button,
  ButtonGroup,
  Spinner,
  Select,
  SelectSection,
  SelectItem,
} from "@heroui/react";
import BuyModal from "../components/BuyModal";
import SellModal from "../components/SellModal";
import ChartModal from "../components/ChartModal";

function Screener() {
  const { liveData, positions, riskpool, historicalTrades } =
    useContext(DataContext);
  const screenOptions = ["VCP", "IPO"];
  const [screenerData, setScreenerData] = useState(null);
  const [screen, setScreen] = useState("VCP");
  const [isBuyModalOpen, setIsBuyModalOpen] = useState(false);
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);
  const [isChartModalOpen, setIsChartModalOpen] = useState(false);
  const [buyData, setBuyData] = useState(null);
  const [sellData, setSellData] = useState(null);
  const [chartData, setChartData] = useState(null);

  const handleOpenBuyModal = () => setIsBuyModalOpen(true);
  const handleCloseBuyModal = () => setIsBuyModalOpen(false);

  const handleOpenSellModal = () => setIsSellModalOpen(true);
  const handleCloseSellModal = () => setIsSellModalOpen(false);

  const handleOpenChartModal = () => setIsChartModalOpen(true);
  const handleCloseChartModal = () => setIsChartModalOpen(false);

  const fetchScreenerData = async () => {
    setScreenerData(null);

    if (screen === "VCP") {
      const response = await fetch(
        "http://localhost:8000/api/screener/vcpscreen"
      );
      const data = await response.json();
      setScreenerData(data);
      console.log("Screener Data", data);
    } else if (screen === "IPO") {
      const response = await fetch(
        "http://localhost:8000/api/screener/iposcreen"
      );
      const data = await response.json();
      setScreenerData(data);
      console.log("Screener Data", data);
    }
  };

  useEffect(() => {
    fetchScreenerData();
  }, [screen]);

  useEffect(() => {
    if (screenerData && liveData) {
      for (const data of screenerData) {
        const liveDataItem = liveData.find(
          (item) => item.instrument_token === data.instrument_token
        );

        // Update 'change' only if 'liveDataItem' exists, otherwise keep the previous value
        if (liveDataItem) {
          data.change = liveDataItem.change;
          data.last_price = liveDataItem.last_price;
        }
      }
      screenerData.sort((a, b) => b.change + 1 - a.change);
    }
  }, [liveData, screenerData]);

  const populateChartData = (row) => {
    setChartData({
      symbol: row.symbol,
      token: row.instrument_token,
    });
  };

  const populateBuyData = (row) => {
    setBuyData({
      symbol: row.symbol,
      instrument_token: row.instrument_token,
      available_risk: riskpool?.data?.available_risk,
      used_risk: riskpool?.data?.used_risk,
      last_price: row.last_price,
    });
  };

  const populateSellData = (row) => {
    setSellData({
      symbol: row.symbol,
      instrument_token: row.instrument_token,
      available_risk: riskpool?.data?.available_risk,
      used_risk: riskpool?.data?.used_risk,
      last_price: row.last_price,
    });
  };

  return (
    <div className="px-6">
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
      <div className="flex items-center justify-between my-3">
        <div className="flex items-center w-1/3 jus">
          <Button onPress={fetchScreenerData}>Refresh Screener</Button>

          <select
            className="w-32 p-2.5 mx-4 text-sm rounded-xl bg-zinc-700"
            label="Screen"
            onChange={(e) => setScreen(e.target.value)}
            disabled={screenerData == null}
          >
            {screenOptions.map((option) => (
              <option key={option}>{option}</option>
            ))}
          </select>
        </div>

        {screenerData != null ? (
          <span> Screen Count: {screenerData.length}</span>
        ) : null}
      </div>
      {screenerData != null ? (
        <Table
          aria-label="Example static collection table"
          className="m-auto  overflow-y-scroll h-[80vh] no-scrollbar"
          align="center"
        >
          <TableHeader>
            <TableColumn>Symbol</TableColumn>
            <TableColumn>Last Price</TableColumn>
            <TableColumn>Change</TableColumn>
            <TableColumn>SMA 50</TableColumn>
            <TableColumn>SMA 150</TableColumn>
            <TableColumn>SMA 200</TableColumn>
            <TableColumn>ATR %</TableColumn>
            <TableColumn>Actions</TableColumn>
          </TableHeader>
          <TableBody className="no-scrollbar">
            {screenerData?.map((row) => (
              <TableRow
                key={row?.symbol}
                className="cursor-pointer hover:bg-zinc-800"
              >
                <TableCell>{row?.symbol}</TableCell>
                <TableCell
                  className={
                    row?.change > 0 ? "text-green-500" : "text-red-500"
                  }
                >
                  {row?.last_price}
                </TableCell>
                <TableCell
                  className={
                    row?.change > 0 ? "text-green-500" : "text-red-500"
                  }
                >
                  {row?.change?.toFixed(2)} %
                </TableCell>

                <TableCell>{row?.sma_50?.toFixed(2)}</TableCell>
                <TableCell>{row?.sma_150?.toFixed(2)}</TableCell>
                <TableCell>{row?.sma_200?.toFixed(2)}</TableCell>
                <TableCell>
                  {((row?.atr / row?.last_price) * 100).toFixed(2)}%
                </TableCell>
                <TableCell>
                  <ButtonGroup>
                    <Button
                      isIconOnly
                      color="success"
                      variant="flat"
                      onPress={() => {
                        populateBuyData(row);
                        handleOpenBuyModal();
                      }}
                    >
                      En
                    </Button>
                    <Button
                      isIconOnly
                      color="danger"
                      variant="flat"
                      onPress={() => {
                        populateSellData(row);
                        handleOpenSellModal();
                      }}
                    >
                      Ex
                    </Button>

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
            ))}
          </TableBody>
        </Table>
      ) : (
        <div className="flex flex-col justify-center items-center w-full h-[85vh]">
          <Spinner size="lg" />
          <span className="m-5 text-2xl">Loading Screener Data</span>
        </div>
      )}
    </div>
  );
}

export default Screener;
