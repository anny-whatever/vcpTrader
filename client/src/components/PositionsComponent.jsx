import React from "react";
import {
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Divider,
  Switch,
} from "@nextui-org/react";
import Logo from "../components/Logo";
import { useContext, useState, useEffect } from "react";
import { DataContext } from "../utils/DataContext";

function PositionCard({ positions }) {
  const { liveData } = useContext(DataContext);
  const [positionsWithPnL, setPositionsWithPnL] = useState([]);
  const [lastKnownData, setLastKnownData] = useState([]);
  const [niftyData, setNiftyData] = useState(null);

  const [basketMultiplier, setBasketMultiplier] = useState(30);

  useEffect(() => {
    if (!liveData) {
      return;
    } else {
      for (const data of liveData) {
        if (data.instrument_token === 256265) {
          setNiftyData(data);
          // console.log(data);
        }
      }
    }
  }, [liveData]);

  const calculatePnL = (position, liveData, lastKnownData) => {
    // Get current or last-known data for buy leg
    const buyLeg =
      liveData?.find(
        (data) => data.instrument_token === position.buy_strike_instrument_token
      ) ||
      lastKnownData.find(
        (data) => data.instrument_token === position.buy_strike_instrument_token
      );

    // Get current or last-known data for sell leg
    const sellLeg =
      liveData?.find(
        (data) =>
          data.instrument_token === position.sell_strike_instrument_token
      ) ||
      lastKnownData.find(
        (data) =>
          data.instrument_token === position.sell_strike_instrument_token
      );

    let buyPnL = 0;
    let sellPnL = 0;

    if (buyLeg) {
      buyPnL =
        (buyLeg.last_price - position.buy_strike_entry_price) * position.qty;
    }
    if (sellLeg) {
      sellPnL =
        (position.sell_strike_entry_price - sellLeg.last_price) * position.qty;
    }

    return { total: buyPnL + sellPnL, buy: buyPnL, sell: sellPnL };
  };

  useEffect(() => {
    // Update positions with PnL
    const updatedPositions = positions?.data?.map((position) => ({
      ...position,
      pnl: calculatePnL(position, liveData, lastKnownData).total,
      buy_pnl: calculatePnL(position, liveData, lastKnownData).buy,
      sell_pnl: calculatePnL(position, liveData, lastKnownData).sell,
    }));

    setPositionsWithPnL(updatedPositions);

    // Update last-known data with current live data
    setLastKnownData((prevData) => {
      const updatedCache = [...prevData];
      liveData?.forEach((data) => {
        const index = updatedCache.findIndex(
          (item) => item.instrument_token === data.instrument_token
        );
        if (index >= 0) {
          updatedCache[index] = data; // Update existing data
        } else {
          updatedCache.push(data); // Add new data
        }
      });
      return updatedCache;
    });
  }, [positions, liveData]);

  const formatKey = (key) => {
    return key
      .replace(/_/g, " ") // Replace underscores with spaces
      .replace(/\b\w/g, (char) => char.toUpperCase()); // Capitalize each word
  };

  return (
    <div className="flex flex-wrap w-full gap-4">
      {positionsWithPnL?.map((position, index) => (
        <Card className="min-w-[300px]" key={index}>
          <CardHeader className="flex items-end gap-3">
            <Logo />
            <div className="flex justify-end text-2xl">
              {formatKey(position.type || `Card ${index + 1}`)}
            </div>
          </CardHeader>
          <Divider />
          <CardBody>
            {position.entry_price && (
              <p className="text-lg">
                <span className="font-light">Entry Price:</span>{" "}
                {position.entry_price.toFixed(2)}
              </p>
            )}
            {position.stop_loss_level && (
              <p className="text-lg">
                <span className="font-light">Stop Loss Level:</span>{" "}
                <span className="text-red-500">
                  {position.stop_loss_level.toFixed(2)} (
                  {Math.abs(
                    position.stop_loss_level - position.entry_price
                  ).toFixed(2)}
                  )
                </span>
              </p>
            )}
            {position.target_level && (
              <p className="text-lg">
                <span className="font-light ">Target Level:</span>{" "}
                <span className="text-green-500">
                  {position.target_level.toFixed(2)} (
                  {Math.abs(
                    position.target_level - position.entry_price
                  ).toFixed(2)}
                  )
                </span>
              </p>
            )}
            {position.qty && (
              <p className="text-lg">
                <span className="font-light">Quantity:</span>{" "}
                {position.qty * basketMultiplier}
              </p>
            )}
          </CardBody>
          <Divider />

          <CardFooter className="flex justify-between">
            <span>
              {position?.pnl && (
                <p className="text-lg">
                  <span className="font-light">P&L:</span>{" "}
                  <span
                    className={
                      position?.pnl > 0 ? "text-green-500" : "text-red-500"
                    }
                  >
                    {position?.pnl > 0
                      ? "+" + position?.pnl.toFixed(2) * basketMultiplier
                      : position?.pnl.toFixed(2) * basketMultiplier}
                  </span>
                </p>
              )}
            </span>
            <span>
              {position?.type.includes("short") ? (
                <p
                  className={
                    position.entry_price - niftyData?.last_price > 0
                      ? "text-green-500"
                      : "text-red-500"
                  }
                >
                  Δ: {(position.entry_price - niftyData?.last_price).toFixed(2)}
                </p>
              ) : (
                <p
                  className={
                    niftyData?.last_price - position?.entry_price > 0
                      ? "text-green-500"
                      : "text-red-500"
                  }
                >
                  Δ:{" "}
                  {(niftyData?.last_price - position?.entry_price).toFixed(2)}
                </p>
              )}
            </span>
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}

export default PositionCard;
